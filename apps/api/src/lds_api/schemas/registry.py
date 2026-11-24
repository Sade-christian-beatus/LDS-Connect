"""Schémas du registre. Les schémas « Public* » ne contiennent que des données publiables
(mineurs : nom d'usage, poste, équipe, âge en années — jamais la date de naissance)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from lds_api.models.enums import (
    Foot,
    LicenceStatus,
    MembershipKind,
    MembershipStatus,
    Position,
    StaffFunction,
)


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Public -------------------------------------------------------------------
class RegionOut(ORM):
    id: uuid.UUID
    name: str
    slug: str


class PoolOut(ORM):
    id: uuid.UUID
    code: str
    name: str
    host_city: str


class SeasonOut(ORM):
    id: uuid.UUID
    name: str
    year: int
    starts_on: date
    ends_on: date
    pools: list[PoolOut]


class PublicTeam(ORM):
    id: uuid.UUID
    name: str
    short_name: str
    acronym: str | None
    slug: str
    primary_color: str
    secondary_color: str
    logo_url: str | None = None
    region: RegionOut
    pool_code: str | None = None


class PublicPlayer(BaseModel):
    person_id: uuid.UUID  # lien vers la fiche publique du joueur
    display_name: str
    position: Position
    age: int
    shirt_number: int | None


class PublicStaff(BaseModel):
    display_name: str
    function: StaffFunction


class PublicTeamDetail(PublicTeam):
    players: list[PublicPlayer]
    staff: list[PublicStaff]


# --- Interne (back-office) ----------------------------------------------------
class PersonIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    display_name: str | None = Field(default=None, max_length=120)
    birth_date: date
    birth_place: str | None = Field(default=None, max_length=120)
    nationality: str = Field(default="BF", min_length=2, max_length=2)
    cnib_number: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=30)
    guardian_consent_on: date | None = None


class PlayerCreate(PersonIn):
    position: Position
    preferred_foot: Foot | None = None
    residence_region_id: uuid.UUID | None = None
    residence_since: date | None = None
    fbf_licence_number: str | None = Field(default=None, max_length=40)
    shirt_number: int | None = Field(default=None, ge=1, le=99)


class PlayerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    display_name: str | None = Field(default=None, max_length=120)
    birth_date: date | None = None
    birth_place: str | None = None
    cnib_number: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=30)
    guardian_consent_on: date | None = None
    position: Position | None = None
    preferred_foot: Foot | None = None
    residence_region_id: uuid.UUID | None = None
    residence_since: date | None = None
    residence_verified: bool | None = None
    fbf_licence_number: str | None = None
    shirt_number: int | None = Field(default=None, ge=1, le=99)


class StaffCreate(PersonIn):
    function: StaffFunction
    qualification: str | None = Field(default=None, max_length=120)


class StaffUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    display_name: str | None = Field(default=None, max_length=120)
    birth_date: date | None = None
    cnib_number: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=30)
    function: StaffFunction | None = None
    qualification: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    short_name: str | None = Field(default=None, max_length=40)
    acronym: str | None = Field(default=None, max_length=16)
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    secondary_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    city: str | None = None


class LicenceBrief(ORM):
    id: uuid.UUID
    number: str
    status: LicenceStatus
    valid_until: date


class SquadMember(BaseModel):
    membership_id: uuid.UUID
    person_id: uuid.UUID
    kind: MembershipKind
    status: MembershipStatus
    first_name: str
    last_name: str
    display_name: str
    birth_date: date
    age: int
    shirt_number: int | None
    position: Position | None = None
    function: StaffFunction | None = None
    is_local: bool | None = None
    residence_region: str | None = None
    residence_region_id: uuid.UUID | None = None
    residence_since: date | None = None
    residence_verified: bool | None = None
    residence_pending: bool = False
    preferred_foot: Foot | None = None
    fbf_licence_number: str | None = None
    qualification: str | None = None
    birth_place: str | None = None
    nationality: str
    guardian_consent_on: date | None = None
    is_minor: bool
    has_cnib: bool
    has_phone: bool
    has_photo: bool = False
    licence: LicenceBrief | None


class TeamOverview(BaseModel):
    """Synthèse d'une équipe pour le tableau de bord du registre."""

    team: PublicTeam
    players: int
    staff: int
    youth_players: int
    local_players: int
    licences_active: int
    licences_missing: int
    licences_blocked: int
    compliant: bool
    issues: list[str]


class AuditEntry(ORM):
    id: int
    at: datetime
    actor_label: str
    action: str
    entity_type: str
    entity_id: str | None
    changes: dict | None
    ip_address: str | None


class RuleCheck(BaseModel):
    code: str
    label: str
    ok: bool
    detail: str


class Squad(BaseModel):
    team: PublicTeam
    members: list[SquadMember]
    compliance: list[RuleCheck]


class SensitiveData(BaseModel):
    person_id: uuid.UUID
    cnib_number: str | None
    phone: str | None


class RulesOut(ORM):
    """Règles sportives de la saison (information publique)."""

    points_win: int
    points_draw: int
    points_loss: int
    tiebreakers: list[str]
    max_squad_players: int
    max_staff: int
    min_age: int
    youth_age_limit: int
    min_youth_players: int
    age_reference_date: date | None
    min_local_starters_ratio: float
    residence_min_months: int
    starters_count: int
    max_substitutes_on_sheet: int
    max_substitutions: int
    match_duration_minutes: int
    yellow_cards_threshold: int
    red_card_ban_matches: int
    qualifiers_per_pool: int
    third_place_match: bool
    knockout_pairings: list[list[str]]
    prize_money: dict[str, int]
