"""Calendrier : génération des journées de poule, phases finales, modification des matchs."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from lds_api.core.errors import BusinessError, NotFound
from lds_api.domain import knockout
from lds_api.domain.round_robin import berger_rounds
from lds_api.models import Match, MatchSheet, Pool, Season, TeamEntry, Venue
from lds_api.models.enums import MatchPhase, MatchStatus
from lds_api.schemas import fixtures as fs
from lds_api.services import audit, seasons

# Créneaux par défaut d'une journée de 5 matchs dans un même stade
DEFAULT_SLOTS = [
    fs.Slot(day_offset=0, time=time(15, 0)),
    fs.Slot(day_offset=0, time=time(17, 30)),
    fs.Slot(day_offset=1, time=time(15, 0)),
    fs.Slot(day_offset=1, time=time(17, 30)),
    fs.Slot(day_offset=2, time=time(16, 0)),
]


def match_query():
    return select(Match).options(
        selectinload(Match.home_team),
        selectinload(Match.away_team),
        selectinload(Match.venue),
        selectinload(Match.pool),
    )


def to_out(m: Match) -> fs.MatchOut:
    return fs.MatchOut(
        id=m.id,
        phase=m.phase,
        pool_code=m.pool.code if m.pool else None,
        round_number=m.round_number,
        bracket_slot=m.bracket_slot,
        home=fs.TeamRef.model_validate(m.home_team) if m.home_team else None,
        away=fs.TeamRef.model_validate(m.away_team) if m.away_team else None,
        venue=fs.VenueOut.model_validate(m.venue) if m.venue else None,
        kickoff_at=m.kickoff_at,
        status=m.status,
        home_score=m.home_score,
        away_score=m.away_score,
        home_penalties=m.home_penalties,
        away_penalties=m.away_penalties,
        live_minute=m.live_minute,
    )


def _venue_for_city(db: Session, city: str) -> Venue | None:
    return db.scalar(select(Venue).where(Venue.city == city).order_by(Venue.name))


def generate_group_fixtures(
    db: Session, actor, pool: Pool, params: fs.GenerateFixturesIn
) -> list[Match]:
    existing = list(
        db.scalars(select(Match).where(Match.pool_id == pool.id, Match.phase == MatchPhase.GROUP))
    )
    if existing:
        locked = [m for m in existing if m.status != MatchStatus.SCHEDULED]
        with_sheet = db.scalar(
            select(MatchSheet.id).where(MatchSheet.match_id.in_([m.id for m in existing]))
        )
        if locked or with_sheet:
            raise BusinessError(
                "Des matchs de cette poule ont déjà commencé : régénération impossible",
                code="fixtures_locked",
            )
        if not params.force:
            raise BusinessError(
                "Le calendrier de cette poule existe déjà (utiliser « force » pour le remplacer)",
                code="fixtures_exist",
            )
        db.execute(delete(Match).where(Match.id.in_([m.id for m in existing])))
        audit.record(db, actor, "delete", "fixtures", pool.id, {"matches": len(existing)})

    entries = list(
        db.scalars(
            select(TeamEntry)
            .where(TeamEntry.pool_id == pool.id)
            .order_by(TeamEntry.draw_position, TeamEntry.id)
        )
    )
    if len(entries) < 2:
        raise BusinessError("La poule doit contenir au moins deux équipes")
    rounds = berger_rounds([e.team_id for e in entries], seed=params.seed)
    venue = _venue_for_city(db, pool.host_city)
    slots = params.slots or DEFAULT_SLOTS

    created: list[Match] = []
    for r_idx, pairs in enumerate(rounds):
        round_date: date | None = (
            params.first_date + timedelta(days=r_idx * params.days_between_rounds)
            if params.first_date
            else None
        )
        for m_idx, (home, away) in enumerate(pairs):
            kickoff = None
            if round_date is not None:
                slot = slots[m_idx % len(slots)]
                kickoff = datetime.combine(
                    round_date + timedelta(days=slot.day_offset), slot.time, tzinfo=UTC
                )
            m = Match(
                season_id=pool.season_id,
                phase=MatchPhase.GROUP,
                pool_id=pool.id,
                round_number=r_idx + 1,
                home_team_id=home,
                away_team_id=away,
                venue_id=venue.id if venue else None,
                kickoff_at=kickoff,
                status=MatchStatus.SCHEDULED,
            )
            db.add(m)
            created.append(m)
    db.flush()
    audit.record(
        db,
        actor,
        "generate",
        "fixtures",
        pool.id,
        {"pool": pool.code, "rounds": len(rounds), "matches": len(created), "seed": params.seed},
    )
    return created


def update_match(db: Session, actor, match: Match, body: fs.MatchUpdate) -> Match:
    data = body.model_dump(exclude_unset=True)
    if "venue_id" in data and data["venue_id"] is not None and not db.get(Venue, data["venue_id"]):
        raise NotFound("Stade")
    if "status" in data and data["status"] == MatchStatus.FINISHED:
        raise BusinessError(
            "Un match est terminé par la validation de sa feuille de match", code="use_sheet"
        )
    for k, v in data.items():
        setattr(match, k, v)
    changes = audit.diff(match)
    if changes:
        audit.record(db, actor, "update", "match", match.id, changes)
    return match


# --- Phases finales -------------------------------------------------------------
def ensure_knockout_matches(db: Session, actor, season: Season) -> list[Match]:
    """Crée les cases du tableau final (équipes inconnues) si elles n'existent pas."""
    rules = seasons.rules_for(db, season)
    slots = list(knockout.SLOT_PHASE)
    if not rules.third_place_match:
        slots.remove("P3")
    existing = {
        m.bracket_slot: m
        for m in db.scalars(
            select(Match).where(Match.season_id == season.id, Match.bracket_slot.is_not(None))
        )
    }
    created = []
    for slot in slots:
        if slot not in existing:
            m = Match(
                season_id=season.id,
                phase=MatchPhase(knockout.SLOT_PHASE[slot]),
                bracket_slot=slot,
                status=MatchStatus.SCHEDULED,
            )
            db.add(m)
            created.append(m)
    if created:
        db.flush()
        audit.record(
            db, actor, "create", "bracket", season.id, {"slots": [m.bracket_slot for m in created]}
        )
    return [*existing.values(), *created]


def refresh_knockout(db: Session, season: Season) -> None:
    """Renseigne les équipes connues du tableau final (après chaque résultat validé)."""
    from lds_api.services import standings as standings_service

    bracket = {
        m.bracket_slot: m
        for m in db.scalars(
            select(Match).where(Match.season_id == season.id, Match.bracket_slot.is_not(None))
        )
    }
    if not bracket:
        return
    rules = seasons.rules_for(db, season)

    pools = list(db.scalars(select(Pool).where(Pool.season_id == season.id)))
    if pools and all(standings_service.group_stage_complete(db, p) for p in pools):
        rankings = {
            p.code: [r.team for r in standings_service.compute_rows(db, p, season)] for p in pools
        }
        qf = knockout.quarter_finals(rules.knockout_pairings, rankings, rules.qualifiers_per_pool)
        for slot, (home, away) in qf.items():
            m = bracket.get(slot)
            if m and m.status == MatchStatus.SCHEDULED:
                m.home_team_id, m.away_team_id = home, away

    results = {
        slot: knockout.KnockoutResult(
            m.home_team_id, m.away_team_id, m.home_score, m.away_score,
            m.home_penalties, m.away_penalties,
        )
        for slot, m in bracket.items()
        if m.status == MatchStatus.FINISHED and m.home_score is not None
    }  # fmt: skip
    for slot, (home, away) in knockout.resolve_later_rounds(
        results, third_place=rules.third_place_match
    ).items():
        m = bracket.get(slot)
        if m and m.status == MatchStatus.SCHEDULED:
            m.home_team_id, m.away_team_id = home, away
    db.flush()
