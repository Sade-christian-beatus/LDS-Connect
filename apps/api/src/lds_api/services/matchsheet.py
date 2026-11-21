"""Feuille de match : composition, événements, validation, suspensions."""

import uuid
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from lds_api.core.errors import BusinessError, NotFound
from lds_api.domain import discipline, knockout, lineup_rules, match_events
from lds_api.domain.eligibility import age_on, is_local
from lds_api.models import (
    LineupEntry,
    Match,
    MatchEvent,
    MatchSheet,
    Person,
    SquadMembership,
    Suspension,
    Team,
)
from lds_api.models.enums import (
    EventType,
    LicenceStatus,
    LineupRole,
    MatchPhase,
    MatchStatus,
    MembershipKind,
    MembershipStatus,
    RoleCode,
    SheetStatus,
    SuspensionReason,
    SuspensionStatus,
)
from lds_api.realtime import bus
from lds_api.schemas import matchsheet as ms
from lds_api.schemas.fixtures import TeamRef
from lds_api.services import audit, fixtures, seasons, standings

EDITABLE_EVENTS = {SheetStatus.SUBMITTED}


# --- Accès ----------------------------------------------------------------------
def get_sheet(db: Session, match_id: uuid.UUID, *, create: bool = False) -> MatchSheet:
    match = db.get(Match, match_id)
    if match is None:
        raise NotFound("Match")
    sheet = db.scalar(select(MatchSheet).where(MatchSheet.match_id == match_id))
    if sheet is None:
        if not create:
            raise NotFound("Feuille de match")
        if match.home_team_id is None or match.away_team_id is None:
            raise BusinessError("Les deux équipes du match ne sont pas encore connues")
        sheet = MatchSheet(match_id=match_id, status=SheetStatus.DRAFT, version=1)
        db.add(sheet)
        db.flush()
    return sheet


def ensure_can_edit(actor, sheet: MatchSheet) -> None:
    """Un délégué n'édite que les feuilles qui lui sont attribuées (si attribution il y a)."""
    roles = actor.user.role_codes
    is_admin = roles & {RoleCode.SUPER_ADMIN, RoleCode.ADMIN_COMPETITION}
    if not is_admin and sheet.delegate_user_id and sheet.delegate_user_id != actor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Feuille attribuée à un autre délégué")


def _require_status(sheet: MatchSheet, *allowed: SheetStatus) -> None:
    if sheet.status not in allowed:
        labels = {
            SheetStatus.DRAFT: "brouillon",
            SheetStatus.SUBMITTED: "soumise",
            SheetStatus.VALIDATED: "validée",
            SheetStatus.CLOSED: "clôturée",
        }
        raise BusinessError(
            f"Action impossible : la feuille est {labels[sheet.status]}", code="sheet_status"
        )


def _touch(sheet: MatchSheet) -> None:
    sheet.version += 1


# --- Éligibilité ------------------------------------------------------------------
def _match_day(match: Match, season) -> date:
    return match.kickoff_at.date() if match.kickoff_at else max(date.today(), season.starts_on)


def _candidates(db: Session, match: Match, team: Team) -> list[ms.CandidateOut]:
    season = seasons.current_season(db)
    rules = seasons.rules_for(db, season)
    day = _match_day(match, season)
    suspended = set(
        db.scalars(
            select(Suspension.person_id).where(
                Suspension.season_id == season.id,
                Suspension.status == SuspensionStatus.ACTIVE,
            )
        )
    )
    members = db.scalars(
        select(SquadMembership)
        .where(
            SquadMembership.team_id == team.id,
            SquadMembership.season_id == season.id,
            SquadMembership.kind == MembershipKind.PLAYER,
            SquadMembership.status == MembershipStatus.ACTIVE,
        )
        .options(
            selectinload(SquadMembership.person).selectinload(Person.player),
            selectinload(SquadMembership.licence),
        )
        .order_by(SquadMembership.shirt_number.nulls_last())
    )
    out = []
    for m in members:
        p, pl, lic = m.person, m.person.player, m.licence
        if pl is None:
            continue
        out.append(
            ms.CandidateOut(
                person_id=p.id,
                display_name=p.display_name,
                full_name=f"{p.first_name} {p.last_name}",
                position=pl.position,
                shirt_number=m.shirt_number,
                age=age_on(p.birth_date, day),
                is_local=is_local(
                    residence_region_id=pl.residence_region_id,
                    residence_since=pl.residence_since,
                    team_region_id=team.region_id,
                    on=day,
                    min_months=rules.residence_min_months,
                ),
                licence_number=lic.number if lic else None,
                licence_ok=bool(
                    lic
                    and lic.status == LicenceStatus.ACTIVE
                    and lic.valid_from <= day <= lic.valid_until
                ),
                is_suspended=p.id in suspended,
            )
        )
    return out


def _lineup_rules(rules) -> lineup_rules.LineupRules:
    return lineup_rules.LineupRules(
        starters_count=rules.starters_count,
        max_substitutes=rules.max_substitutes_on_sheet,
        min_local_starters_ratio=rules.min_local_starters_ratio,
        min_age=rules.min_age,
    )


def _team_view(db: Session, sheet: MatchSheet, team: Team, rules) -> ms.TeamSheetOut:
    cands = {c.person_id: c for c in _candidates(db, sheet.match, team)}
    entries = [e for e in sheet.lineup if e.team_id == team.id]
    checked = []
    lineup_out = []
    for e in entries:
        c = cands.get(e.person_id)
        name = c.display_name if c else e.person.display_name
        checked.append(
            lineup_rules.Candidate(
                person_id=e.person_id,
                name=name,
                role=e.role.value,
                shirt_number=e.shirt_number,
                is_captain=e.is_captain,
                is_goalkeeper=e.is_goalkeeper,
                is_squad_member=c is not None,
                licence_ok=bool(c and c.licence_ok),
                is_suspended=bool(c and c.is_suspended),
                is_local=bool(c and c.is_local),
                age=c.age if c else 0,
            )
        )
        lineup_out.append(
            ms.LineupEntryOut(
                person_id=e.person_id,
                role=e.role,
                shirt_number=e.shirt_number,
                is_captain=e.is_captain,
                is_goalkeeper=e.is_goalkeeper,
                display_name=name,
                is_local=bool(c and c.is_local),
            )
        )
    lr = _lineup_rules(rules)
    violations = lineup_rules.check_lineup(checked, lr)
    return ms.TeamSheetOut(
        team=TeamRef.model_validate(team),
        candidates=list(cands.values()),
        lineup=lineup_out,
        violations=[ms.ViolationOut(**v.__dict__) for v in violations],
        local_starters=sum(c.is_local for c in checked if c.role == lineup_rules.STARTER),
        local_starters_required=lineup_rules.min_local_starters(
            lr.starters_count, lr.min_local_starters_ratio
        ),
    )


# --- Événements -------------------------------------------------------------------
def _domain_events(events) -> list[match_events.Event]:
    return [
        match_events.Event(
            type=e.type.value,
            minute=e.minute,
            team=e.team_id,
            person=e.person_id,
            related=e.related_person_id,
            added_time=e.added_time,
        )
        for e in events
    ]


def _team_sheets(sheet: MatchSheet) -> list[match_events.TeamSheet]:
    out = []
    for team_id in (sheet.match.home_team_id, sheet.match.away_team_id):
        entries = [e for e in sheet.lineup if e.team_id == team_id]
        out.append(
            match_events.TeamSheet(
                team=team_id,
                starters=frozenset(e.person_id for e in entries if e.role == LineupRole.STARTER),
                substitutes=frozenset(
                    e.person_id for e in entries if e.role == LineupRole.SUBSTITUTE
                ),
            )
        )
    return out


def _event_errors(sheet: MatchSheet, events, rules) -> list[str]:
    return match_events.check_events(
        _domain_events(events), _team_sheets(sheet), max_substitutions=rules.max_substitutions
    )


def _event_out(e: MatchEvent) -> ms.EventOut:
    return ms.EventOut(
        id=e.id,
        client_uuid=e.client_uuid,
        team_id=e.team_id,
        type=e.type,
        minute=e.minute,
        added_time=e.added_time,
        person_id=e.person_id,
        person_name=e.person.display_name,
        related_person_id=e.related_person_id,
        related_person_name=e.related_person.display_name if e.related_person else None,
    )


# --- Vue complète -----------------------------------------------------------------
def view(db: Session, sheet: MatchSheet) -> ms.SheetOut:
    db.refresh(sheet)
    season = seasons.current_season(db)
    rules = seasons.rules_for(db, season)
    match = db.scalar(fixtures.match_query().where(Match.id == sheet.match_id))
    events = sorted(sheet.events, key=lambda e: (e.minute, e.added_time or 0, e.created_at))
    return ms.SheetOut(
        id=sheet.id,
        match=fixtures.to_out(match),
        status=sheet.status,
        version=sheet.version,
        referee_name=sheet.referee_name,
        assistant_referees=sheet.assistant_referees,
        attendance=sheet.attendance,
        notes=sheet.notes,
        submitted_at=sheet.submitted_at,
        validated_at=sheet.validated_at,
        closed_at=sheet.closed_at,
        home=_team_view(db, sheet, match.home_team, rules),
        away=_team_view(db, sheet, match.away_team, rules),
        events=[_event_out(e) for e in events],
        event_errors=_event_errors(sheet, events, rules),
        max_substitutions=rules.max_substitutions,
        starters_count=rules.starters_count,
        max_substitutes=rules.max_substitutes_on_sheet,
    )


# --- Actions ----------------------------------------------------------------------
def set_lineup(db: Session, actor, sheet: MatchSheet, team_id: uuid.UUID, body: ms.LineupIn):
    _require_status(sheet, SheetStatus.DRAFT)
    match = sheet.match
    if team_id not in (match.home_team_id, match.away_team_id):
        raise BusinessError("Cette équipe ne joue pas ce match")
    ids = [e.person_id for e in body.entries]
    if len(ids) != len(set(ids)):
        raise BusinessError("Un joueur figure deux fois dans la composition")
    db.execute(
        delete(LineupEntry).where(LineupEntry.sheet_id == sheet.id, LineupEntry.team_id == team_id)
    )
    team = db.get(Team, team_id)
    locals_ = {c.person_id: c.is_local for c in _candidates(db, match, team)}
    for e in body.entries:
        db.add(
            LineupEntry(
                sheet_id=sheet.id,
                team_id=team_id,
                person_id=e.person_id,
                role=e.role,
                shirt_number=e.shirt_number,
                is_captain=e.is_captain,
                is_goalkeeper=e.is_goalkeeper,
                is_local_snapshot=locals_.get(e.person_id, False),
            )
        )
    _touch(sheet)
    db.flush()
    db.expire(sheet, ["lineup"])
    audit.record(
        db,
        actor,
        "set_lineup",
        "match_sheet",
        sheet.id,
        {"team_id": team_id, "entries": [e.model_dump(mode="json") for e in body.entries]},
    )


def update_header(db: Session, actor, sheet: MatchSheet, body: ms.SheetHeaderIn) -> None:
    _require_status(sheet, SheetStatus.DRAFT, SheetStatus.SUBMITTED)
    data = body.model_dump(exclude_unset=True)
    match = sheet.match
    if "delegate_user_id" in data and not (
        actor.user.role_codes & {RoleCode.SUPER_ADMIN, RoleCode.ADMIN_COMPETITION}
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Attribution réservée à l'administration")
    for key in ("home_penalties", "away_penalties"):
        if key in data:
            if match.phase == MatchPhase.GROUP and data[key] is not None:
                raise BusinessError("Pas de tirs au but en phase de poules")
            setattr(match, key, data.pop(key))
    for k, v in data.items():
        setattr(sheet, k, v)
    changes = {**audit.diff(sheet), **audit.diff(match)}
    if changes:
        _touch(sheet)
        audit.record(db, actor, "update", "match_sheet", sheet.id, changes)


def submit(db: Session, actor, sheet: MatchSheet) -> None:
    """Verrouille les compositions après contrôle des règles ; le match passe en direct."""
    _require_status(sheet, SheetStatus.DRAFT)
    v = view(db, sheet)
    problems = {
        v.home.team.short_name: [x.message for x in v.home.violations],
        v.away.team.short_name: [x.message for x in v.away.violations],
    }
    if any(problems.values()):
        raise BusinessError(
            "Composition non conforme : corriger avant de soumettre",
            code="lineup_invalid",
            details=problems,
        )
    sheet.status = SheetStatus.SUBMITTED
    sheet.submitted_at = datetime.now(UTC)
    match = sheet.match
    match.status = MatchStatus.LIVE
    match.home_score, match.away_score, match.live_minute = 0, 0, 0
    _touch(sheet)
    audit.record(db, actor, "submit", "match_sheet", sheet.id)
    _publish(db, match)


def reopen(db: Session, actor, sheet: MatchSheet) -> None:
    """Retour en brouillon (correction de composition avant le coup d'envoi)."""
    _require_status(sheet, SheetStatus.SUBMITTED)
    if sheet.events:
        raise BusinessError("Des événements sont déjà saisis : réouverture impossible")
    sheet.status = SheetStatus.DRAFT
    sheet.submitted_at = None
    match = sheet.match
    match.status = MatchStatus.SCHEDULED
    match.home_score = match.away_score = match.live_minute = None
    _touch(sheet)
    audit.record(db, actor, "reopen", "match_sheet", sheet.id)
    _publish(db, match)


def add_event(db: Session, actor, sheet: MatchSheet, body: ms.EventIn) -> MatchEvent:
    """Ajout idempotent (client_uuid) : rejouer la même action hors ligne ne crée pas de doublon."""
    existing = db.scalar(select(MatchEvent).where(MatchEvent.client_uuid == body.client_uuid))
    if existing is not None:
        if existing.sheet_id != sheet.id:
            raise BusinessError("Identifiant d'événement déjà utilisé")
        return existing
    _require_status(sheet, *EDITABLE_EVENTS)
    rules = seasons.rules_for(db, seasons.current_season(db))
    event = MatchEvent(
        sheet_id=sheet.id,
        team_id=body.team_id,
        type=body.type,
        minute=body.minute,
        added_time=body.added_time,
        person_id=body.person_id,
        related_person_id=body.related_person_id,
        client_uuid=body.client_uuid,
        created_by_id=actor.id,
    )
    errors = _event_errors(sheet, [*sheet.events, event], rules)
    if errors:
        raise BusinessError(errors[0], code="event_invalid", details=errors)
    db.add(event)
    db.flush()
    db.expire(sheet, ["events"])
    _touch(sheet)
    _update_live(db, sheet)
    audit.record(db, actor, "create", "match_event", event.id, body.model_dump(mode="json"))
    return event


def delete_event(db: Session, actor, sheet: MatchSheet, event_id: uuid.UUID) -> None:
    _require_status(sheet, *EDITABLE_EVENTS)
    event = db.get(MatchEvent, event_id)
    if event is None or event.sheet_id != sheet.id:
        raise NotFound("Événement")
    rules = seasons.rules_for(db, seasons.current_season(db))
    remaining = [e for e in sheet.events if e.id != event_id]
    errors = _event_errors(sheet, remaining, rules)
    if errors:
        raise BusinessError(
            "Suppression impossible : " + errors[0], code="event_dependency", details=errors
        )
    audit.record(db, actor, "delete", "match_event", event.id, audit.snapshot(event))
    db.delete(event)
    db.flush()
    db.expire(sheet, ["events"])
    _touch(sheet)
    _update_live(db, sheet)


def _update_live(db: Session, sheet: MatchSheet) -> None:
    match = sheet.match
    events = sheet.events
    match.home_score, match.away_score = match_events.score(
        _domain_events(events), match.home_team_id, match.away_team_id
    )
    match.live_minute = max((e.minute for e in events), default=0)
    _publish(db, match)


def _publish(db: Session, match: Match) -> None:
    db.flush()
    m = db.scalar(fixtures.match_query().where(Match.id == match.id))
    bus.publish(fixtures.to_out(m).model_dump_json())


def validate(db: Session, actor, sheet: MatchSheet) -> None:
    """Fin de match : score officiel, classement, suspensions, tableau final."""
    _require_status(sheet, SheetStatus.SUBMITTED)
    season = seasons.current_season(db)
    rules = seasons.rules_for(db, season)
    events = list(sheet.events)
    errors = _event_errors(sheet, events, rules)
    if errors:
        raise BusinessError(errors[0], code="event_invalid", details=errors)
    match = sheet.match
    home, away = match_events.score(_domain_events(events), match.home_team_id, match.away_team_id)
    if match.phase != MatchPhase.GROUP:
        try:
            winner, _ = knockout.winner_loser(
                knockout.KnockoutResult(
                    match.home_team_id,
                    match.away_team_id,
                    home,
                    away,
                    match.home_penalties,
                    match.away_penalties,
                )
            )
        except ValueError as exc:
            raise BusinessError(str(exc), code="penalties_required") from exc
        match.winner_team_id = winner
    else:
        match.home_penalties = match.away_penalties = None

    match.home_score, match.away_score = home, away
    match.status = MatchStatus.FINISHED
    match.live_minute = None
    sheet.status = SheetStatus.VALIDATED
    sheet.validated_at = datetime.now(UTC)
    sheet.validated_by_id = actor.id
    _touch(sheet)
    db.flush()

    _serve_suspensions(db, season, match)
    created = _create_suspensions(db, actor, season, rules, match, events)
    audit.record(
        db,
        actor,
        "validate",
        "match_sheet",
        sheet.id,
        {"score": [home, away], "suspensions": len(created)},
    )
    standings.invalidate_after_commit(db, match.pool_id)
    fixtures.refresh_knockout(db, season)
    _publish(db, match)


def close(db: Session, actor, sheet: MatchSheet) -> None:
    _require_status(sheet, SheetStatus.VALIDATED)
    sheet.status = SheetStatus.CLOSED
    sheet.closed_at = datetime.now(UTC)
    _touch(sheet)
    audit.record(db, actor, "close", "match_sheet", sheet.id)


# --- Discipline -------------------------------------------------------------------
def _serve_suspensions(db: Session, season, match: Match) -> None:
    """Un match validé purge une journée de suspension pour les joueurs de ces équipes."""
    active = db.scalars(
        select(Suspension).where(
            Suspension.season_id == season.id,
            Suspension.status == SuspensionStatus.ACTIVE,
            Suspension.team_id.in_([match.home_team_id, match.away_team_id]),
            Suspension.source_match_id != match.id,
        )
    )
    for s in active:
        s.matches_served += 1
        if s.matches_served >= s.matches_count:
            s.status = SuspensionStatus.SERVED


def _prior_yellows(db: Session, season, rules, match: Match) -> dict[uuid.UUID, int]:
    q = (
        select(MatchEvent.person_id, MatchEvent.type, MatchSheet.match_id)
        .join(MatchSheet, MatchSheet.id == MatchEvent.sheet_id)
        .join(Match, Match.id == MatchSheet.match_id)
        .where(
            Match.season_id == season.id,
            Match.id != match.id,
            MatchSheet.status.in_([SheetStatus.VALIDATED, SheetStatus.CLOSED]),
            MatchEvent.type.in_([EventType.YELLOW_CARD, EventType.SECOND_YELLOW]),
        )
    )
    if rules.reset_yellows_after_group_stage and match.phase != MatchPhase.GROUP:
        q = q.where(Match.phase != MatchPhase.GROUP)
    rows = list(db.execute(q))
    expelled = {(p, m) for p, t, m in rows if t == EventType.SECOND_YELLOW}
    counts: dict[uuid.UUID, int] = {}
    for person, etype, match_id in rows:
        if etype == EventType.YELLOW_CARD and (person, match_id) not in expelled:
            counts[person] = counts.get(person, 0) + 1
    return counts


def _create_suspensions(db, actor, season, rules, match: Match, events) -> list[Suspension]:
    cards = [
        discipline.Card(e.person_id, e.type.value)
        for e in events
        if e.type in (EventType.YELLOW_CARD, EventType.SECOND_YELLOW, EventType.RED_CARD)
    ]
    if not cards:
        return []
    team_of = {e.person_id: e.team_id for e in events}
    new = discipline.suspensions_for_match(
        cards,
        _prior_yellows(db, season, rules, match),
        discipline.DisciplineRules(
            yellow_cards_threshold=rules.yellow_cards_threshold,
            yellow_accumulation_ban_matches=rules.yellow_accumulation_ban_matches,
            red_card_ban_matches=rules.red_card_ban_matches,
            second_yellow_ban_matches=rules.second_yellow_ban_matches,
        ),
    )
    created = []
    for n in new:
        s = Suspension(
            season_id=season.id,
            person_id=n.person,
            team_id=team_of[n.person],
            reason=SuspensionReason(n.reason),
            source_match_id=match.id,
            matches_count=n.matches,
            notes="Suspension automatique",
        )
        db.add(s)
        created.append(s)
    db.flush()
    for s in created:
        audit.record(db, actor, "create", "suspension", s.id, audit.snapshot(s))
    return created
