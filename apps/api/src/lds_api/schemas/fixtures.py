"""Schémas : matchs, calendrier, classements, tableau final."""

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from lds_api.models.enums import MatchPhase, MatchStatus


class TeamRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    short_name: str
    slug: str
    primary_color: str
    secondary_color: str
    logo_url: str | None = None


class VenueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city: str
    is_confirmed: bool
    capacity: int | None = None
    address: str | None = None


class MatchOut(BaseModel):
    id: uuid.UUID
    phase: MatchPhase
    pool_code: str | None
    round_number: int | None
    bracket_slot: str | None
    home: TeamRef | None
    away: TeamRef | None
    venue: VenueOut | None
    kickoff_at: datetime | None
    status: MatchStatus
    home_score: int | None
    away_score: int | None
    home_penalties: int | None
    away_penalties: int | None
    live_minute: int | None


class StandingRow(BaseModel):
    rank: int
    team: TeamRef
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    form: list[str]
    needs_draw: bool
    qualified_zone: bool


class PoolStandings(BaseModel):
    pool_code: str
    pool_name: str
    host_city: str
    matches_played: int
    matches_total: int
    rows: list[StandingRow]


class Slot(BaseModel):
    day_offset: int = Field(ge=0, le=6)
    time: time


class GenerateFixturesIn(BaseModel):
    first_date: date | None = None
    days_between_rounds: int = Field(default=7, ge=1, le=60)
    # Créneaux d'une journée (jour relatif + heure locale, Ouagadougou = UTC)
    slots: list[Slot] | None = None
    seed: int | None = None
    force: bool = False


class MatchUpdate(BaseModel):
    venue_id: uuid.UUID | None = None
    kickoff_at: datetime | None = None
    status: MatchStatus | None = None


class VenueIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=80)
    capacity: int | None = Field(default=None, ge=0)
    address: str | None = None
    is_confirmed: bool = False
