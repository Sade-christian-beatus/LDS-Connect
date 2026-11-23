"""Schémas des talents : tableau de bord, fiches joueur (interne et publique), suivi, notes."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from lds_api.models.enums import Foot, Position
from lds_api.schemas.fixtures import MatchOut, TeamRef

STAT_FIELDS = (
    "appearances",
    "starts",
    "minutes_played",
    "goals",
    "assists",
    "yellow_cards",
    "red_cards",
    "clean_sheets",
    "man_of_the_match",
)

SortKey = Literal[
    "goals",
    "assists",
    "minutes_played",
    "appearances",
    "goals_per_90",
    "contributions_per_90",
    "clean_sheets",
    "man_of_the_match",
    "avg_rating",
    "age",
]


class StatValues(BaseModel):
    appearances: int
    starts: int
    minutes_played: int
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    clean_sheets: int
    man_of_the_match: int
    goals_per_90: float | None  # None sous 90 minutes jouées
    contributions_per_90: float | None  # (buts + passes) sur 90 minutes


class DashboardFilters(BaseModel):
    position: Position | None = None
    age_min: int | None = Field(default=None, ge=10, le=60)
    age_max: int | None = Field(default=None, ge=10, le=60)
    team_id: uuid.UUID | None = None
    region_id: uuid.UUID | None = None
    pool: str | None = Field(default=None, max_length=2)
    min_minutes: int = Field(default=0, ge=0)
    watched_only: bool = False
    q: str | None = Field(default=None, max_length=80)
    sort: SortKey = "goals"
    limit: int = Field(default=100, ge=1, le=800)


class DashboardRow(StatValues):
    person_id: uuid.UUID
    full_name: str
    display_name: str
    position: Position
    age: int
    is_youth: bool  # sous la limite d'âge « jeunes » des règles de la saison
    team: TeamRef
    region: str | None
    shirt_number: int | None
    watched: bool
    avg_rating: float | None
    notes_count: int


class Dashboard(BaseModel):
    total: int
    youth_age_limit: int
    match_duration_minutes: int
    rows: list[DashboardRow]


class MatchLog(BaseModel):
    match: MatchOut
    team_id: uuid.UUID
    started: bool
    minutes: int
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    clean_sheet: bool


class PublicPlayerProfile(BaseModel):
    person_id: uuid.UUID
    display_name: str
    position: Position
    age: int
    shirt_number: int | None
    team: TeamRef
    stats: StatValues
    matches: list[MatchLog]


class NoteOut(BaseModel):
    id: uuid.UUID
    author: str
    rating: int | None
    body: str
    match_id: uuid.UUID | None
    created_at: datetime


class TalentProfile(BaseModel):
    person_id: uuid.UUID
    full_name: str
    display_name: str
    position: Position
    preferred_foot: Foot | None
    age: int
    is_youth: bool
    shirt_number: int | None
    team: TeamRef
    region: str | None
    stats: StatValues
    matches: list[MatchLog]
    watched: bool
    tags: list[str]
    notes: list[NoteOut]


class WatchIn(BaseModel):
    watched: bool
    tags: list[str] = Field(default_factory=list, max_length=10)


class NoteIn(BaseModel):
    body: str = Field(min_length=3, max_length=4000)
    rating: int | None = Field(default=None, ge=1, le=5)
    match_id: uuid.UUID | None = None


class NoteDelete(BaseModel):
    reason: str = Field(min_length=3, max_length=255)
