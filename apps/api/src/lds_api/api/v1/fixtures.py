"""Calendrier, résultats, classements et tableau final (public) ; gestion (admin)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select

from lds_api.core.deps import Actor, DbSession, require
from lds_api.core.errors import NotFound
from lds_api.core.rbac import Perm
from lds_api.models import Match, Pool, Team, Venue
from lds_api.models.enums import MatchPhase, MatchStatus
from lds_api.schemas import fixtures as fs
from lds_api.services import fixtures, seasons, standings, stats

router = APIRouter(tags=["calendrier"])


# --- Public -----------------------------------------------------------------
@router.get("/matches", response_model=list[fs.MatchOut])
def list_matches(
    db: DbSession,
    pool: Annotated[str | None, Query(description="Code de poule : A ou B")] = None,
    round: Annotated[int | None, Query(ge=1, description="Journée")] = None,  # noqa: A002
    team: Annotated[str | None, Query(description="Slug de l'équipe")] = None,
    phase: MatchPhase | None = None,
    status_: Annotated[MatchStatus | None, Query(alias="status")] = None,
):
    season = seasons.current_season(db)
    q = fixtures.match_query().where(Match.season_id == season.id)
    if pool:
        q = q.join(Pool, Pool.id == Match.pool_id).where(Pool.code == pool.upper())
    if round:
        q = q.where(Match.round_number == round)
    if phase:
        q = q.where(Match.phase == phase)
    if status_:
        q = q.where(Match.status == status_)
    if team:
        t = db.scalar(select(Team).where(Team.slug == team))
        if t is None:
            raise NotFound("Équipe")
        q = q.where((Match.home_team_id == t.id) | (Match.away_team_id == t.id))
    q = q.order_by(Match.kickoff_at.nulls_last(), Match.round_number, Match.bracket_slot)
    return [fixtures.to_out(m) for m in db.scalars(q)]


@router.get("/matches/{match_id}", response_model=fs.MatchOut)
def get_match(match_id: uuid.UUID, db: DbSession):
    m = db.scalar(fixtures.match_query().where(Match.id == match_id))
    if m is None:
        raise NotFound("Match")
    return fixtures.to_out(m)


@router.get("/standings", response_model=list[fs.PoolStandings])
def get_standings(db: DbSession):
    return standings.all_standings(db)


@router.get("/bracket", response_model=list[fs.MatchOut])
def get_bracket(db: DbSession):
    season = seasons.current_season(db)
    q = fixtures.match_query().where(Match.season_id == season.id, Match.bracket_slot.is_not(None))
    order = {s: i for i, s in enumerate(["QF1", "QF2", "QF3", "QF4", "SF1", "SF2", "P3", "F"])}
    return sorted((fixtures.to_out(m) for m in db.scalars(q)), key=lambda m: order[m.bracket_slot])


@router.get("/stats", response_model=stats.SeasonStats)
def season_stats(db: DbSession, limit: Annotated[int, Query(ge=1, le=100)] = 20):
    """Meilleurs buteurs et passeurs (feuilles validées). Nom d'usage uniquement."""
    return stats.season_stats(db, seasons.current_season(db).id, limit=limit)


@router.get("/venues", response_model=list[fs.VenueOut])
def list_venues(db: DbSession):
    return list(db.scalars(select(Venue).order_by(Venue.city, Venue.name)))


# --- Administration -------------------------------------------------------------
@router.post(
    "/admin/pools/{pool_id}/fixtures",
    response_model=list[fs.MatchOut],
    status_code=status.HTTP_201_CREATED,
)
def generate_fixtures(
    pool_id: uuid.UUID,
    body: fs.GenerateFixturesIn,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.FIXTURE_MANAGE))],
):
    pool = db.get(Pool, pool_id)
    if pool is None:
        raise NotFound("Poule")
    created = fixtures.generate_group_fixtures(db, actor, pool, body)
    db.commit()
    ids = [m.id for m in created]
    q = fixtures.match_query().where(Match.id.in_(ids)).order_by(Match.round_number)
    return [fixtures.to_out(m) for m in db.scalars(q)]


@router.patch("/admin/matches/{match_id}", response_model=fs.MatchOut)
def update_match(
    match_id: uuid.UUID,
    body: fs.MatchUpdate,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.FIXTURE_MANAGE))],
):
    m = db.get(Match, match_id)
    if m is None:
        raise NotFound("Match")
    fixtures.update_match(db, actor, m, body)
    db.commit()
    return get_match(match_id, db)


@router.post("/admin/bracket", response_model=list[fs.MatchOut])
def create_bracket(
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.FIXTURE_MANAGE))],
):
    season = seasons.current_season(db)
    fixtures.ensure_knockout_matches(db, actor, season)
    fixtures.refresh_knockout(db, season)
    db.commit()
    return get_bracket(db)


@router.post("/admin/venues", response_model=fs.VenueOut, status_code=status.HTTP_201_CREATED)
def create_venue(
    body: fs.VenueIn,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.FIXTURE_MANAGE))],
):
    from lds_api.services import audit

    v = Venue(**body.model_dump())
    db.add(v)
    db.flush()
    audit.record(db, actor, "create", "venue", v.id, body.model_dump())
    db.commit()
    return v
