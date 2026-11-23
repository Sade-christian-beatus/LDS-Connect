"""API publique (sans authentification) : saison, équipes. Données publiques limitées."""

from fastapi import APIRouter
from sqlalchemy import select

from lds_api.core.deps import DbSession
from lds_api.core.errors import NotFound
from lds_api.domain.eligibility import age_on
from lds_api.models import Region, Team
from lds_api.models.enums import MembershipKind
from lds_api.schemas import registry as s
from lds_api.services import registry, seasons

router = APIRouter(tags=["public"])


@router.get("/seasons/current", response_model=s.SeasonOut)
def current_season(db: DbSession):
    return seasons.current_season(db)


@router.get("/rules", response_model=s.RulesOut)
def current_rules(db: DbSession):
    """Règles de la saison courante (barème, effectifs, règle des locaux, discipline…)."""
    return seasons.rules_for(db, seasons.current_season(db))


@router.get("/regions", response_model=list[s.RegionOut])
def list_regions(db: DbSession):
    return list(db.scalars(select(Region).order_by(Region.name)))


@router.get("/teams", response_model=list[s.PublicTeam])
def list_teams(db: DbSession):
    season = seasons.current_season(db)
    teams = db.scalars(select(Team).order_by(Team.name))
    return [registry.public_team(db, t, season) for t in teams]


@router.get("/teams/{slug}", response_model=s.PublicTeamDetail)
def team_detail(slug: str, db: DbSession):
    team = db.scalar(select(Team).where(Team.slug == slug))
    if team is None:
        raise NotFound("Équipe")
    season = seasons.current_season(db)
    rules = seasons.rules_for(db, season)
    ref = seasons.reference_date(season, rules)
    players, staff = [], []
    for m in registry.active_members(db, team.id, season.id):
        p = m.person
        if m.kind == MembershipKind.PLAYER and p.player:
            players.append(
                s.PublicPlayer(
                    person_id=p.id,
                    display_name=p.display_name,
                    position=p.player.position,
                    age=age_on(p.birth_date, ref),
                    shirt_number=m.shirt_number,
                )
            )
        elif m.kind == MembershipKind.STAFF and p.staff:
            staff.append(s.PublicStaff(display_name=p.display_name, function=p.staff.function))
    base = registry.public_team(db, team, season)
    return s.PublicTeamDetail(**base.model_dump(), players=players, staff=staff)
