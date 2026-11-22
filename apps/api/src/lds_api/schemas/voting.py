"""Schémas des votes du public."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from lds_api.models.enums import BallotKind, BallotStatus, ResultsVisibility, VoteStatus
from lds_api.schemas.fixtures import TeamRef


class OptionIn(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    person_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    match_event_id: uuid.UUID | None = None
    media_url: str | None = Field(default=None, max_length=255)


class OptionOut(BaseModel):
    id: uuid.UUID
    label: str
    team: TeamRef | None
    media_url: str | None
    position: int


class OptionResult(BaseModel):
    option_id: uuid.UUID
    label: str
    team: TeamRef | None
    votes: int
    share: float  # part des participants (0..1)
    rank: int


class Results(BaseModel):
    participants: int
    options: list[OptionResult]


class BallotOut(BaseModel):
    id: uuid.UUID
    kind: BallotKind
    title: str
    description: str | None
    match_id: uuid.UUID | None
    opens_at: datetime
    closes_at: datetime
    state: str  # draft | upcoming | open | closed
    max_choices: int
    is_paid: bool
    results_visibility: ResultsVisibility
    results_publish_at: datetime | None
    results_visible: bool
    options: list[OptionOut]
    results: Results | None = None


class BallotAdminOut(BallotOut):
    status: BallotStatus
    flagged_voters: int
    rejected_voters: int


class BallotIn(BaseModel):
    kind: BallotKind
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    match_id: uuid.UUID | None = None
    opens_at: datetime
    closes_at: datetime
    max_choices: int = Field(default=1, ge=1, le=11)
    results_visibility: ResultsVisibility = ResultsVisibility.IMMEDIATE
    results_publish_at: datetime | None = None
    is_paid: bool = False
    options: list[OptionIn] = Field(default_factory=list, max_length=60)


class BallotUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    max_choices: int | None = Field(default=None, ge=1, le=11)
    results_visibility: ResultsVisibility | None = None
    results_publish_at: datetime | None = None
    is_paid: bool | None = None
    options: list[OptionIn] | None = Field(default=None, max_length=60)


class Candidate(BaseModel):
    label: str
    sublabel: str | None
    person_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    match_event_id: uuid.UUID | None = None


class CodeRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=30)
    choices: list[uuid.UUID] = Field(min_length=1, max_length=11)


class CodeSent(BaseModel):
    challenge_id: uuid.UUID
    expires_at: datetime
    phone_hint: str  # ex. « +226 •• •• 34 56 »


class VoteIn(BaseModel):
    challenge_id: uuid.UUID
    code: str = Field(min_length=4, max_length=8)


class VoterOut(BaseModel):
    """Participation vue par l'administration : jamais le numéro, seulement son empreinte."""

    voter: str  # empreinte (index aveugle) du numéro
    cast_at: datetime
    status: VoteStatus
    flag_reason: str | None
    connection: str | None  # empreinte courte de l'adresse IP
    choices: list[str]


class ReviewIn(BaseModel):
    decision: VoteStatus


class ReportOut(BaseModel):
    """Données du procès-verbal (page imprimable côté interface)."""

    ballot: BallotAdminOut
    generated_at: datetime
    generated_by: str
    valid_voters: int
    flagged_voters: int
    rejected_voters: int
    journal_sha256: str  # empreinte du journal CSV : preuve qu'il n'a pas été modifié
