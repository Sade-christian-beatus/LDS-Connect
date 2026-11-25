"""Saisons, règles de compétition et stades (administration)."""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from lds_api.models.enums import SeasonStatus


class RulesFields(BaseModel):
    # Barème
    points_win: int = Field(ge=0, le=10)
    points_draw: int = Field(ge=0, le=10)
    points_loss: int = Field(ge=0, le=10)
    tiebreakers: list[str] = Field(min_length=1, max_length=12)
    # Effectifs
    max_squad_players: int = Field(ge=11, le=60)
    max_staff: int = Field(ge=1, le=20)
    min_age: int = Field(ge=10, le=25)
    youth_age_limit: int = Field(ge=12, le=30)
    min_youth_players: int = Field(ge=0, le=40)
    age_reference_date: date | None = None
    # Règle des locaux
    min_local_starters_ratio: Decimal = Field(ge=0, le=1, decimal_places=3)
    residence_min_months: int = Field(ge=0, le=60)
    # Feuille de match
    starters_count: int = Field(ge=7, le=11)
    max_substitutes_on_sheet: int = Field(ge=0, le=15)
    max_substitutions: int = Field(ge=0, le=15)
    match_duration_minutes: int = Field(ge=20, le=120)
    # Discipline
    yellow_cards_threshold: int = Field(ge=1, le=10)
    yellow_accumulation_ban_matches: int = Field(ge=0, le=10)
    red_card_ban_matches: int = Field(ge=0, le=20)
    second_yellow_ban_matches: int = Field(ge=0, le=10)
    reset_yellows_after_group_stage: bool
    # Phases finales et dotations
    qualifiers_per_pool: int = Field(ge=1, le=8)
    third_place_match: bool
    knockout_pairings: list[list[str]]
    prize_money: dict[str, int]


class RulesAdminOut(RulesFields):
    model_config = ConfigDict(from_attributes=True)

    season_id: uuid.UUID
    # Règles qui changent classements, suspensions ou statistiques : figées dès le premier match
    locked_fields: list[str]
    season_started: bool


class RulesUpdate(BaseModel):
    """Modification partielle : seuls les champs envoyés changent."""

    points_win: int | None = Field(None, ge=0, le=10)
    points_draw: int | None = Field(None, ge=0, le=10)
    points_loss: int | None = Field(None, ge=0, le=10)
    tiebreakers: list[str] | None = Field(None, min_length=1, max_length=12)
    max_squad_players: int | None = Field(None, ge=11, le=60)
    max_staff: int | None = Field(None, ge=1, le=20)
    min_age: int | None = Field(None, ge=10, le=25)
    youth_age_limit: int | None = Field(None, ge=12, le=30)
    min_youth_players: int | None = Field(None, ge=0, le=40)
    age_reference_date: date | None = None
    min_local_starters_ratio: Decimal | None = Field(None, ge=0, le=1, decimal_places=3)
    residence_min_months: int | None = Field(None, ge=0, le=60)
    starters_count: int | None = Field(None, ge=7, le=11)
    max_substitutes_on_sheet: int | None = Field(None, ge=0, le=15)
    max_substitutions: int | None = Field(None, ge=0, le=15)
    match_duration_minutes: int | None = Field(None, ge=20, le=120)
    yellow_cards_threshold: int | None = Field(None, ge=1, le=10)
    yellow_accumulation_ban_matches: int | None = Field(None, ge=0, le=10)
    red_card_ban_matches: int | None = Field(None, ge=0, le=20)
    second_yellow_ban_matches: int | None = Field(None, ge=0, le=10)
    reset_yellows_after_group_stage: bool | None = None
    qualifiers_per_pool: int | None = Field(None, ge=1, le=8)
    third_place_match: bool | None = None
    knockout_pairings: list[list[str]] | None = None
    prize_money: dict[str, int] | None = None
    reason: str = Field(min_length=3, max_length=255)


class SeasonAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    year: int
    starts_on: date
    ends_on: date
    status: SeasonStatus
    is_current: bool
    teams: int = 0
    matches: int = 0


class SeasonCreate(BaseModel):
    year: int = Field(ge=2020, le=2100)
    name: str = Field(min_length=3, max_length=80)
    starts_on: date
    ends_on: date
    # Copie des règles, des poules et des engagements d'équipes de la saison courante
    copy_from_current: bool = True


class SeasonUpdate(BaseModel):
    name: str = Field(min_length=3, max_length=80)


class VenueUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    city: str | None = Field(None, min_length=2, max_length=80)
    capacity: int | None = Field(None, ge=0, le=200_000)
    address: str | None = Field(None, max_length=255)
    is_confirmed: bool | None = None
