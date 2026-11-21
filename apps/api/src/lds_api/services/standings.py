"""Classements des poules : calculés depuis les résultats validés, mis en cache dans Redis."""

import contextlib
import logging
import uuid

import redis
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from lds_api.core.ratelimit import get_redis
from lds_api.domain.standings import Points, Result, Row, compute_standings
from lds_api.models import Match, MatchEvent, MatchSheet, Pool, Season, Team, TeamEntry
from lds_api.models.enums import EventType, MatchPhase, MatchStatus, SheetStatus
from lds_api.schemas import fixtures as fs
from lds_api.services import seasons

log = logging.getLogger(__name__)
CACHE_TTL = 300

# Barème de fair-play (à confirmer par la Ligue) : jaune 1, 2e jaune 3, rouge direct 3
FAIR_PLAY_POINTS = {EventType.YELLOW_CARD: 1, EventType.SECOND_YELLOW: 3, EventType.RED_CARD: 3}


# Cache versionné : la version n'est incrémentée qu'APRÈS le commit d'un résultat. Un calcul
# commencé avant ce commit écrit sous l'ancienne version, que plus personne ne lit : un
# classement périmé ne peut donc jamais être servi après une validation.
def _version_key(pool_id: uuid.UUID) -> str:
    return f"standings:ver:{pool_id}"


def _cache_key(pool_id: uuid.UUID, version: int) -> str:
    return f"standings:{pool_id}:v{version}"


def invalidate(pool_id: uuid.UUID | None) -> None:
    """Invalidation immédiate (données déjà validées en base)."""
    if pool_id is None:
        return
    try:
        get_redis().incr(_version_key(pool_id))
    except redis.RedisError:
        log.warning("Redis indisponible : invalidation du classement ignorée")


def invalidate_after_commit(db: Session, pool_id: uuid.UUID | None) -> None:
    """Invalidation déclenchée seulement une fois la transaction validée."""
    if pool_id is not None:
        event.listen(db, "after_commit", lambda _s: invalidate(pool_id), once=True)


def _group_matches(db: Session, pool: Pool):
    return select(Match).where(Match.pool_id == pool.id, Match.phase == MatchPhase.GROUP)


def group_stage_complete(db: Session, pool: Pool) -> bool:
    total = db.scalar(select(func.count()).select_from(_group_matches(db, pool).subquery()))
    done = db.scalar(
        select(func.count()).select_from(
            _group_matches(db, pool).where(Match.status == MatchStatus.FINISHED).subquery()
        )
    )
    return bool(total) and total == done


def _fair_play(db: Session, pool: Pool) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(MatchEvent.team_id, MatchEvent.type, func.count())
        .join(MatchSheet, MatchSheet.id == MatchEvent.sheet_id)
        .join(Match, Match.id == MatchSheet.match_id)
        .where(
            Match.pool_id == pool.id,
            Match.phase == MatchPhase.GROUP,
            MatchSheet.status.in_([SheetStatus.VALIDATED, SheetStatus.CLOSED]),
            MatchEvent.type.in_(list(FAIR_PLAY_POINTS)),
        )
        .group_by(MatchEvent.team_id, MatchEvent.type)
    )
    out: dict[uuid.UUID, int] = {}
    for team_id, etype, n in rows:
        out[team_id] = out.get(team_id, 0) + FAIR_PLAY_POINTS[etype] * n
    return out


def compute_rows(db: Session, pool: Pool, season: Season) -> list[Row]:
    rules = seasons.rules_for(db, season)
    team_ids = list(db.scalars(select(TeamEntry.team_id).where(TeamEntry.pool_id == pool.id)))
    finished = db.scalars(
        _group_matches(db, pool)
        .where(Match.status == MatchStatus.FINISHED, Match.home_score.is_not(None))
        .order_by(Match.round_number, Match.kickoff_at)
    )
    results = [Result(m.home_team_id, m.away_team_id, m.home_score, m.away_score) for m in finished]
    return compute_standings(
        team_ids,
        results,
        points=Points(rules.points_win, rules.points_draw, rules.points_loss),
        tiebreakers=rules.tiebreakers,
        fair_play=_fair_play(db, pool),
    )


def pool_standings(db: Session, pool: Pool, season: Season) -> fs.PoolStandings:
    version: int | None = None
    try:
        version = int(get_redis().get(_version_key(pool.id)) or 0)
        cached = get_redis().get(_cache_key(pool.id, version))
        if cached:
            return fs.PoolStandings.model_validate_json(cached)
    except redis.RedisError:
        log.warning("Redis indisponible : classement recalculé sans cache")

    rules = seasons.rules_for(db, season)
    rows = compute_rows(db, pool, season)
    teams = {t.id: t for t in db.scalars(select(Team).where(Team.id.in_([r.team for r in rows])))}
    total = db.scalar(select(func.count()).select_from(_group_matches(db, pool).subquery()))
    played = db.scalar(
        select(func.count()).select_from(
            _group_matches(db, pool).where(Match.status == MatchStatus.FINISHED).subquery()
        )
    )
    out = fs.PoolStandings(
        pool_code=pool.code,
        pool_name=pool.name,
        host_city=pool.host_city,
        matches_played=played,
        matches_total=total,
        rows=[
            fs.StandingRow(
                rank=r.rank,
                team=fs.TeamRef.model_validate(teams[r.team]),
                played=r.played,
                won=r.won,
                drawn=r.drawn,
                lost=r.lost,
                goals_for=r.goals_for,
                goals_against=r.goals_against,
                goal_difference=r.goal_difference,
                points=r.points,
                form=r.form[-5:],
                needs_draw=r.needs_draw,
                qualified_zone=r.rank <= rules.qualifiers_per_pool,
            )
            for r in rows
        ],
    )
    with contextlib.suppress(redis.RedisError):
        if version is not None:
            get_redis().set(_cache_key(pool.id, version), out.model_dump_json(), ex=CACHE_TTL)
    return out


def all_standings(db: Session) -> list[fs.PoolStandings]:
    season = seasons.current_season(db)
    pools = db.scalars(select(Pool).where(Pool.season_id == season.id).order_by(Pool.code))
    return [pool_standings(db, p, season) for p in pools]
