"""Accès à la saison courante et à ses règles."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from lds_api.core.errors import NotFound
from lds_api.models import CompetitionRules, Season


def current_season(db: Session) -> Season:
    season = db.scalar(select(Season).where(Season.is_current.is_(True)))
    if season is None:
        raise NotFound("Saison courante")
    return season


def rules_for(db: Session, season: Season) -> CompetitionRules:
    rules = db.scalar(select(CompetitionRules).where(CompetitionRules.season_id == season.id))
    if rules is None:
        raise NotFound("Règles de la saison")
    return rules


def reference_date(season: Season, rules: CompetitionRules):
    return rules.age_reference_date or season.starts_on
