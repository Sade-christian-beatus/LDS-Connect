"""Schémas de la feuille de match."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from lds_api.models.enums import EventType, LineupRole, Position, SheetStatus
from lds_api.schemas.fixtures import MatchOut, TeamRef


class LineupEntryIn(BaseModel):
    person_id: uuid.UUID
    role: LineupRole
    shirt_number: int | None = Field(default=None, ge=1, le=99)
    is_captain: bool = False
    is_goalkeeper: bool = False


class LineupIn(BaseModel):
    entries: list[LineupEntryIn] = Field(max_length=40)


class CandidateOut(BaseModel):
    """Joueur de l'effectif, avec son éligibilité pour ce match."""

    person_id: uuid.UUID
    display_name: str
    full_name: str
    position: Position
    shirt_number: int | None
    age: int
    is_local: bool
    licence_number: str | None
    licence_ok: bool
    is_suspended: bool


class LineupEntryOut(LineupEntryIn):
    display_name: str
    is_local: bool


class ViolationOut(BaseModel):
    code: str
    message: str
    person_id: uuid.UUID | None = None


class TeamSheetOut(BaseModel):
    team: TeamRef
    candidates: list[CandidateOut]
    lineup: list[LineupEntryOut]
    violations: list[ViolationOut]
    local_starters: int
    local_starters_required: int


class EventIn(BaseModel):
    client_uuid: uuid.UUID
    team_id: uuid.UUID
    type: EventType
    minute: int = Field(ge=0, le=130)
    added_time: int | None = Field(default=None, ge=0, le=30)
    person_id: uuid.UUID
    related_person_id: uuid.UUID | None = None


class EventOut(BaseModel):
    id: uuid.UUID
    client_uuid: uuid.UUID | None
    team_id: uuid.UUID
    type: EventType
    minute: int
    added_time: int | None
    person_id: uuid.UUID
    person_name: str
    related_person_id: uuid.UUID | None
    related_person_name: str | None


class SheetHeaderIn(BaseModel):
    referee_name: str | None = Field(default=None, max_length=120)
    assistant_referees: str | None = Field(default=None, max_length=255)
    attendance: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=4000)
    home_penalties: int | None = Field(default=None, ge=0, le=50)
    away_penalties: int | None = Field(default=None, ge=0, le=50)
    delegate_user_id: uuid.UUID | None = None


class SheetOut(BaseModel):
    id: uuid.UUID
    match: MatchOut
    status: SheetStatus
    version: int
    referee_name: str | None
    assistant_referees: str | None
    attendance: int | None
    notes: str | None
    submitted_at: datetime | None
    validated_at: datetime | None
    closed_at: datetime | None
    home: TeamSheetOut
    away: TeamSheetOut
    events: list[EventOut]
    event_errors: list[str]
    max_substitutions: int
    starters_count: int
    max_substitutes: int


class DelegateMatch(MatchOut):
    sheet_status: SheetStatus | None
