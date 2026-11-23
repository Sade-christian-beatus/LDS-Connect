"""Talents : statistiques des joueurs (table player_stats, recalculée à chaque validation de
feuille), tableau de bord de la cellule technique, liste de suivi et notes d'observation.

Les notes concernent souvent des mineurs : texte chiffré en base, visibles seulement par
la cellule technique et l'administration, chaque consultation inscrite au journal d'audit.
"""

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lds_api.core.errors import BusinessError, NotFound
from lds_api.domain import talents as calc
from lds_api.domain.eligibility import age_on
from lds_api.models import (
    Ballot,
    BallotOption,
    LineupEntry,
    Match,
    MatchSheet,
    Person,
    PlayerStat,
    Season,
    SquadMembership,
    TalentNote,
    TalentWatch,
    Team,
    TeamEntry,
)
from lds_api.models.enums import (
    BallotKind,
    BallotStatus,
    LineupRole,
    MembershipKind,
    MembershipStatus,
    SheetStatus,
)
from lds_api.schemas import talents as ts
from lds_api.schemas.fixtures import TeamRef
from lds_api.services import audit, fixtures, seasons, voting

OFFICIAL = [SheetStatus.VALIDATED, SheetStatus.CLOSED]


# --- Calcul ---------------------------------------------------------------------------------
def _sheets(db: Session, season: Season, person_ids: set[uuid.UUID] | None = None):
    q = (
        select(MatchSheet)
        .join(Match, Match.id == MatchSheet.match_id)
        .where(Match.season_id == season.id, MatchSheet.status.in_(OFFICIAL))
        .options(selectinload(MatchSheet.lineup), selectinload(MatchSheet.events))
    )
    if person_ids is not None:
        q = q.where(
            MatchSheet.id.in_(
                select(LineupEntry.sheet_id).where(LineupEntry.person_id.in_(person_ids))
            )
        )
    return db.scalars(q).unique().all()


def _lines_for_sheet(sheet: MatchSheet, duration: int) -> list[calc.MatchLine]:
    match = sheet.match
    conceded = {}
    if match.home_team_id and match.away_team_id:
        conceded = {
            match.home_team_id: match.away_score or 0,
            match.away_team_id: match.home_score or 0,
        }
    lineup = [
        calc.LineupLine(e.person_id, e.team_id, e.role == LineupRole.STARTER, e.is_goalkeeper)
        for e in sheet.lineup
    ]
    events = [
        calc.Event(e.type.value, e.minute, e.person_id, e.team_id, e.related_person_id)
        for e in sheet.events
    ]
    return calc.match_lines(lineup, events, duration=duration, conceded=conceded)


def _motm_counts(db: Session, season: Season) -> dict[uuid.UUID, int]:
    """Élections « homme du match » dont les résultats sont publiés (vainqueur(s) au rang 1)."""
    counts: dict[uuid.UUID, int] = defaultdict(int)
    ballots = db.scalars(
        select(Ballot).where(
            Ballot.season_id == season.id,
            Ballot.kind == BallotKind.MAN_OF_THE_MATCH,
            Ballot.status == BallotStatus.PUBLISHED,
        )
    )
    for b in ballots:
        persons = {
            o.id: o.person_id
            for o in db.scalars(select(BallotOption).where(BallotOption.ballot_id == b.id))
        }
        for r in voting.results(db, b).options:
            if r.rank == 1 and r.votes > 0 and persons.get(r.option_id):
                counts[persons[r.option_id]] += 1
    return counts


def refresh(db: Session, season: Season, person_ids: set[uuid.UUID] | None = None) -> int:
    """Recalcule player_stats (tous les joueurs, ou ceux d'une feuille qui vient d'être
    validée). Renvoie le nombre de lignes écrites."""
    duration = seasons.rules_for(db, season).match_duration_minutes
    per_key: dict[tuple[uuid.UUID, uuid.UUID], list[calc.MatchLine]] = defaultdict(list)
    for sheet in _sheets(db, season, person_ids):
        for line in _lines_for_sheet(sheet, duration):
            if person_ids is None or line.person_id in person_ids:
                per_key[(line.person_id, line.team_id)].append(line)
    motm = _motm_counts(db, season)

    existing = {
        (s.person_id, s.team_id): s
        for s in db.scalars(
            select(PlayerStat).where(
                PlayerStat.season_id == season.id,
                *([PlayerStat.person_id.in_(person_ids)] if person_ids is not None else []),
            )
        )
    }
    now = datetime.now(UTC)
    for key in set(existing) | set(per_key):
        t = calc.totals(per_key.get(key, []))
        row = existing.get(key) or PlayerStat(season_id=season.id, person_id=key[0], team_id=key[1])
        row.appearances, row.starts, row.minutes_played = t.appearances, t.starts, t.minutes_played
        row.goals, row.assists = t.goals, t.assists
        row.yellow_cards, row.red_cards, row.clean_sheets = (
            t.yellow_cards,
            t.red_cards,
            t.clean_sheets,
        )
        row.man_of_the_match = motm.get(key[0], 0)
        row.computed_at = now
        db.add(row)
    db.flush()
    return len(set(existing) | set(per_key))


def refresh_for_sheet(db: Session, sheet: MatchSheet) -> None:
    season = db.get(Season, sheet.match.season_id)
    refresh(db, season, {e.person_id for e in sheet.lineup})


# --- Lecture --------------------------------------------------------------------------------
def _members(db: Session, season: Season):
    return db.scalars(
        select(SquadMembership)
        .where(
            SquadMembership.season_id == season.id,
            SquadMembership.kind == MembershipKind.PLAYER,
            SquadMembership.status == MembershipStatus.ACTIVE,
        )
        .options(
            selectinload(SquadMembership.person).selectinload(Person.player),
            selectinload(SquadMembership.team).selectinload(Team.region),
        )
    ).all()


def _stats_by_person(db: Session, season: Season) -> dict[uuid.UUID, PlayerStat]:
    """Une ligne par joueur (cumul si le joueur a changé d'équipe en cours de saison)."""
    out: dict[uuid.UUID, PlayerStat] = {}
    for s in db.scalars(select(PlayerStat).where(PlayerStat.season_id == season.id)):
        cur = out.get(s.person_id)
        if cur is None:
            out[s.person_id] = s
            continue
        merged = PlayerStat(person_id=s.person_id, team_id=s.team_id)
        for f in ts.STAT_FIELDS:
            setattr(merged, f, (getattr(cur, f) or 0) + (getattr(s, f) or 0))
        out[s.person_id] = merged
    return out


def _stat_values(stat: PlayerStat | None) -> dict:
    values = {f: (getattr(stat, f) or 0) if stat else 0 for f in ts.STAT_FIELDS}
    minutes = values["minutes_played"]
    values["goals_per_90"] = calc.per_90(values["goals"], minutes)
    values["contributions_per_90"] = calc.per_90(values["goals"] + values["assists"], minutes)
    return values


def dashboard(db: Session, f: ts.DashboardFilters) -> ts.Dashboard:
    season = seasons.current_season(db)
    rules = seasons.rules_for(db, season)
    ref = seasons.reference_date(season, rules)
    stats = _stats_by_person(db, season)
    watched = set(db.scalars(select(TalentWatch.person_id)))
    ratings: dict[uuid.UUID, list[int]] = defaultdict(list)
    for pid, r in db.execute(
        select(TalentNote.person_id, TalentNote.rating).where(
            TalentNote.deleted_at.is_(None), TalentNote.rating.is_not(None)
        )
    ):
        ratings[pid].append(r)

    pools = {
        e.team_id: e.pool.code
        for e in db.scalars(
            select(TeamEntry)
            .where(TeamEntry.season_id == season.id)
            .options(selectinload(TeamEntry.pool))
        )
        if e.pool
    }
    rows = []
    for m in _members(db, season):
        p, team = m.person, m.team
        if p.player is None:
            continue
        age = age_on(p.birth_date, ref)
        if f.position and p.player.position != f.position:
            continue
        if f.age_max is not None and age > f.age_max:
            continue
        if f.age_min is not None and age < f.age_min:
            continue
        if f.team_id and team.id != f.team_id:
            continue
        if f.region_id and team.region_id != f.region_id:
            continue
        if f.pool and pools.get(team.id) != f.pool:
            continue
        if f.watched_only and p.id not in watched:
            continue
        if f.q and f.q.lower() not in f"{p.first_name} {p.last_name} {p.display_name}".lower():
            continue
        values = _stat_values(stats.get(p.id))
        if values["minutes_played"] < f.min_minutes:
            continue
        notes = ratings.get(p.id, [])
        rows.append(
            ts.DashboardRow(
                person_id=p.id,
                full_name=f"{p.first_name} {p.last_name}",
                display_name=p.display_name,
                position=p.player.position,
                age=age,
                is_youth=age < rules.youth_age_limit,
                team=TeamRef.model_validate(team),
                region=team.region.name if team.region else None,
                shirt_number=m.shirt_number,
                watched=p.id in watched,
                avg_rating=round(sum(notes) / len(notes), 1) if notes else None,
                notes_count=len(notes),
                **values,
            )
        )
    key = f.sort
    rows.sort(key=lambda r: (getattr(r, key) is None, -(getattr(r, key) or 0), r.display_name))
    return ts.Dashboard(
        total=len(rows),
        youth_age_limit=rules.youth_age_limit,
        match_duration_minutes=rules.match_duration_minutes,
        rows=rows[: f.limit],
    )


def _membership(db: Session, season: Season, person_id: uuid.UUID) -> SquadMembership:
    m = db.scalar(
        select(SquadMembership)
        .where(
            SquadMembership.season_id == season.id,
            SquadMembership.person_id == person_id,
            SquadMembership.kind == MembershipKind.PLAYER,
            SquadMembership.status == MembershipStatus.ACTIVE,
        )
        .options(
            selectinload(SquadMembership.person).selectinload(Person.player),
            selectinload(SquadMembership.team).selectinload(Team.region),
        )
    )
    if m is None or m.person.player is None:
        raise NotFound("Joueur introuvable")
    return m


def match_log(db: Session, season: Season, person_id: uuid.UUID) -> list[ts.MatchLog]:
    """Match par match, du plus récent au plus ancien (feuilles validées seulement)."""
    duration = seasons.rules_for(db, season).match_duration_minutes
    out = []
    for sheet in _sheets(db, season, {person_id}):
        line = next(
            (x for x in _lines_for_sheet(sheet, duration) if x.person_id == person_id), None
        )
        if line is None:
            continue
        m = db.scalar(fixtures.match_query().where(Match.id == sheet.match_id))
        out.append(
            ts.MatchLog(
                match=fixtures.to_out(m),
                team_id=line.team_id,
                started=line.started,
                minutes=line.minutes,
                goals=line.goals,
                assists=line.assists,
                yellow_cards=line.yellow_cards,
                red_cards=line.red_cards,
                clean_sheet=line.clean_sheet,
            )
        )
    out.sort(key=lambda x: x.match.kickoff_at or datetime.min.replace(tzinfo=UTC), reverse=True)
    return out


def public_player(db: Session, person_id: uuid.UUID) -> ts.PublicPlayerProfile:
    """Page publique : nom d'usage, poste, équipe, âge, numéro et chiffres de la saison.
    Ni nom complet, ni date de naissance, ni région de résidence (joueurs mineurs)."""
    season = seasons.current_season(db)
    rules = seasons.rules_for(db, season)
    m = _membership(db, season, person_id)
    p = m.person
    return ts.PublicPlayerProfile(
        person_id=p.id,
        display_name=p.display_name,
        position=p.player.position,
        age=age_on(p.birth_date, seasons.reference_date(season, rules)),
        shirt_number=m.shirt_number,
        team=TeamRef.model_validate(m.team),
        stats=ts.StatValues(**_stat_values(_stats_by_person(db, season).get(p.id))),
        matches=match_log(db, season, p.id),
    )


def profile(db: Session, actor, person_id: uuid.UUID) -> ts.TalentProfile:
    """Fiche interne : chiffres, match par match, suivi et notes (consultation journalisée)."""
    season = seasons.current_season(db)
    rules = seasons.rules_for(db, season)
    m = _membership(db, season, person_id)
    p = m.person
    watch = db.scalar(select(TalentWatch).where(TalentWatch.person_id == p.id))
    notes = db.scalars(
        select(TalentNote)
        .where(TalentNote.person_id == p.id, TalentNote.deleted_at.is_(None))
        .order_by(TalentNote.created_at.desc())
    ).all()
    audit.record(db, actor, "read", "talent_notes", p.id, {"notes": len(notes)})
    authors = {u.id: u.full_name for u in _users(db, {n.author_id for n in notes})}
    return ts.TalentProfile(
        person_id=p.id,
        full_name=f"{p.first_name} {p.last_name}",
        display_name=p.display_name,
        position=p.player.position,
        preferred_foot=p.player.preferred_foot,
        age=age_on(p.birth_date, seasons.reference_date(season, rules)),
        is_youth=age_on(p.birth_date, seasons.reference_date(season, rules))
        < rules.youth_age_limit,
        shirt_number=m.shirt_number,
        team=TeamRef.model_validate(m.team),
        region=m.team.region.name if m.team.region else None,
        stats=ts.StatValues(**_stat_values(_stats_by_person(db, season).get(p.id))),
        matches=match_log(db, season, p.id),
        watched=watch is not None,
        tags=watch.tags if watch else [],
        notes=[
            ts.NoteOut(
                id=n.id,
                author=authors.get(n.author_id, "—"),
                rating=n.rating,
                body=n.body,
                match_id=n.match_id,
                created_at=n.created_at,
            )
            for n in notes
        ],
    )


def _users(db: Session, ids: set):
    from lds_api.models import User

    ids = {i for i in ids if i}
    return db.scalars(select(User).where(User.id.in_(ids))).all() if ids else []


# --- Suivi et notes -------------------------------------------------------------------------
def set_watch(db: Session, actor, person_id: uuid.UUID, body: ts.WatchIn) -> None:
    season = seasons.current_season(db)
    _membership(db, season, person_id)
    watch = db.scalar(select(TalentWatch).where(TalentWatch.person_id == person_id))
    tags = sorted({t.strip() for t in body.tags if t.strip()})
    if body.watched:
        if watch is None:
            db.add(
                TalentWatch(person_id=person_id, added_by_id=getattr(actor, "id", None), tags=tags)
            )
        else:
            watch.tags = tags
        audit.record(db, actor, "watch", "talent", person_id, {"tags": tags})
    elif watch is not None:
        db.delete(watch)
        audit.record(db, actor, "unwatch", "talent", person_id, {})


def add_note(db: Session, actor, person_id: uuid.UUID, body: ts.NoteIn) -> None:
    season = seasons.current_season(db)
    _membership(db, season, person_id)
    if body.match_id and db.get(Match, body.match_id) is None:
        raise BusinessError("Match introuvable")
    note = TalentNote(
        person_id=person_id,
        author_id=getattr(actor, "id", None),
        match_id=body.match_id,
        rating=body.rating,
        body=body.body.strip(),
    )
    db.add(note)
    db.flush()
    # Le texte n'est pas recopié dans le journal (il reste chiffré dans sa table)
    audit.record(
        db, actor, "create", "talent_note", note.id, {"person_id": person_id, "rating": body.rating}
    )


def delete_note(db: Session, actor, note_id: uuid.UUID, reason: str) -> None:
    note = db.get(TalentNote, note_id)
    if note is None or note.deleted_at is not None:
        raise NotFound("Note introuvable")
    note.deleted_at = datetime.now(UTC)
    note.deleted_reason = reason
    audit.record(
        db, actor, "delete", "talent_note", note.id, {"person_id": note.person_id, "reason": reason}
    )


def teams_for_filters(db: Session) -> list[TeamRef]:
    return [TeamRef.model_validate(t) for t in db.scalars(select(Team).order_by(Team.name))]
