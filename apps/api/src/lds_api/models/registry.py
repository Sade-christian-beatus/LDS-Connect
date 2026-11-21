"""Registre : saisons, règles, régions, poules, équipes, personnes, effectifs, licences."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lds_api.db.base import Base, Timestamps, UUIDPk
from lds_api.db.types import EncryptedString
from lds_api.models.enums import (
    Foot,
    Gender,
    LicenceStatus,
    MembershipKind,
    MembershipStatus,
    Position,
    SeasonStatus,
    StaffFunction,
    str_enum,
)

DEFAULT_TIEBREAKERS = [
    "points",
    "head_to_head_points",
    "head_to_head_goal_difference",
    "head_to_head_goals_for",
    "goal_difference",
    "goals_for",
    "fair_play",
    "drawing_of_lots",
]


class Season(UUIDPk, Timestamps, Base):
    __tablename__ = "seasons"

    name: Mapped[str] = mapped_column(String(80))
    year: Mapped[int] = mapped_column(Integer, unique=True)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    status: Mapped[SeasonStatus] = mapped_column(str_enum(SeasonStatus), default=SeasonStatus.DRAFT)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    rules: Mapped["CompetitionRules"] = relationship(back_populates="season", uselist=False)
    pools: Mapped[list["Pool"]] = relationship(back_populates="season", order_by="Pool.code")


class CompetitionRules(UUIDPk, Timestamps, Base):
    """Toutes les règles sportives paramétrables d'une saison. Aucune règle codée en dur."""

    __tablename__ = "competition_rules"

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"), unique=True)

    # Barème
    points_win: Mapped[int] = mapped_column(Integer, default=3)
    points_draw: Mapped[int] = mapped_column(Integer, default=1)
    points_loss: Mapped[int] = mapped_column(Integer, default=0)
    # Critères de départage, dans l'ordre (voir domain/standings.py pour les codes)
    tiebreakers: Mapped[list[str]] = mapped_column(JSONB, default=lambda: DEFAULT_TIEBREAKERS)

    # Effectifs
    max_squad_players: Mapped[int] = mapped_column(Integer, default=30)
    max_staff: Mapped[int] = mapped_column(Integer, default=7)
    min_age: Mapped[int] = mapped_column(Integer, default=16)
    youth_age_limit: Mapped[int] = mapped_column(Integer, default=19)  # « moins de 19 ans »
    min_youth_players: Mapped[int] = mapped_column(Integer, default=7)
    # Date de référence pour le calcul des âges (défaut : début de saison)
    age_reference_date: Mapped[date | None] = mapped_column(Date)

    # Règle des locaux
    min_local_starters_ratio: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0.5"))
    residence_min_months: Mapped[int] = mapped_column(Integer, default=6)

    # Feuille de match
    starters_count: Mapped[int] = mapped_column(Integer, default=11)
    max_substitutes_on_sheet: Mapped[int] = mapped_column(Integer, default=9)
    max_substitutions: Mapped[int] = mapped_column(Integer, default=5)

    # Discipline
    yellow_cards_threshold: Mapped[int] = mapped_column(Integer, default=3)
    yellow_accumulation_ban_matches: Mapped[int] = mapped_column(Integer, default=1)
    red_card_ban_matches: Mapped[int] = mapped_column(Integer, default=1)
    second_yellow_ban_matches: Mapped[int] = mapped_column(Integer, default=1)
    reset_yellows_after_group_stage: Mapped[bool] = mapped_column(Boolean, default=True)

    # Phases finales
    qualifiers_per_pool: Mapped[int] = mapped_column(Integer, default=4)
    third_place_match: Mapped[bool] = mapped_column(Boolean, default=True)
    # Croisement des quarts : liste de paires [["A1","B4"], ...] (à confirmer par la Ligue)
    knockout_pairings: Mapped[list[list[str]]] = mapped_column(
        JSONB, default=lambda: [["A1", "B4"], ["B2", "A3"], ["B1", "A4"], ["A2", "B3"]]
    )

    # Dotations en FCFA, par rang final (« quarter_finalist » pour chaque quart-de-finaliste)
    prize_money: Mapped[dict[str, int]] = mapped_column(
        JSONB,
        default=lambda: {
            "1": 24_000_000,
            "2": 17_000_000,
            "3": 15_000_000,
            "4": 12_000_000,
            "quarter_finalist": 8_000_000,
        },
    )

    season: Mapped[Season] = relationship(back_populates="rules")


class Region(UUIDPk, Base):
    __tablename__ = "regions"

    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)


class Pool(UUIDPk, Base):
    __tablename__ = "pools"
    __table_args__ = (UniqueConstraint("season_id", "code"),)

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"))
    code: Mapped[str] = mapped_column(String(4))  # « A », « B »
    name: Mapped[str] = mapped_column(String(80))
    host_city: Mapped[str] = mapped_column(String(80))

    season: Mapped[Season] = relationship(back_populates="pools")
    entries: Mapped[list["TeamEntry"]] = relationship(back_populates="pool")


class Team(UUIDPk, Timestamps, Base):
    __tablename__ = "teams"

    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regions.id"))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    short_name: Mapped[str] = mapped_column(String(40))
    acronym: Mapped[str | None] = mapped_column(String(16))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    # Emplacement générique (initiales + couleur) tant que les logos officiels ne sont pas fournis
    primary_color: Mapped[str] = mapped_column(String(7), default="#1f7a3a")
    secondary_color: Mapped[str] = mapped_column(String(7), default="#ffffff")
    logo_path: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(80))

    region: Mapped[Region] = relationship()


class TeamEntry(UUIDPk, Base):
    """Engagement d'une équipe dans une saison, avec sa poule."""

    __tablename__ = "team_entries"
    __table_args__ = (UniqueConstraint("season_id", "team_id"),)

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"))
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"))
    pool_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pools.id"))
    # Numéro de tirage dans la poule (1..10), utilisé par le générateur de calendrier
    draw_position: Mapped[int | None] = mapped_column(Integer)

    team: Mapped[Team] = relationship()
    pool: Mapped[Pool | None] = relationship(back_populates="entries")


class Person(UUIDPk, Timestamps, Base):
    """Identité commune aux joueurs et encadreurs. Données sensibles chiffrées."""

    __tablename__ = "persons"

    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    # Nom d'usage : seul nom affiché publiquement
    display_name: Mapped[str] = mapped_column(String(120))
    birth_date: Mapped[date] = mapped_column(Date)
    birth_place: Mapped[str | None] = mapped_column(String(120))
    gender: Mapped[Gender] = mapped_column(str_enum(Gender, 1), default=Gender.MALE)
    nationality: Mapped[str] = mapped_column(String(2), default="BF")

    cnib_number: Mapped[str | None] = mapped_column(EncryptedString)
    cnib_index: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(EncryptedString)
    phone_index: Mapped[str | None] = mapped_column(String(64), index=True)
    photo_path: Mapped[str | None] = mapped_column(String(255))
    # Mineurs : autorisation parentale (question ouverte : exigence à confirmer)
    guardian_consent_on: Mapped[date | None] = mapped_column(Date)

    player: Mapped["Player | None"] = relationship(back_populates="person", uselist=False)
    staff: Mapped["Staff | None"] = relationship(back_populates="person", uselist=False)


class Player(UUIDPk, Timestamps, Base):
    __tablename__ = "players"

    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), unique=True)
    position: Mapped[Position] = mapped_column(str_enum(Position, 2))
    preferred_foot: Mapped[Foot | None] = mapped_column(str_enum(Foot, 8))
    # Résidence : base du statut « local » (calculé, voir domain/eligibility.py)
    residence_region_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regions.id"))
    residence_since: Mapped[date | None] = mapped_column(Date)
    residence_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    fbf_licence_number: Mapped[str | None] = mapped_column(String(40))

    person: Mapped[Person] = relationship(back_populates="player")
    residence_region: Mapped[Region | None] = relationship()


class Staff(UUIDPk, Timestamps, Base):
    __tablename__ = "staff"

    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), unique=True)
    function: Mapped[StaffFunction] = mapped_column(str_enum(StaffFunction))
    qualification: Mapped[str | None] = mapped_column(String(120))

    person: Mapped[Person] = relationship(back_populates="staff")


class SquadMembership(UUIDPk, Timestamps, Base):
    """Appartenance d'une personne à l'effectif d'une équipe pour une saison."""

    __tablename__ = "squad_memberships"
    __table_args__ = (
        UniqueConstraint("season_id", "person_id"),
        UniqueConstraint("season_id", "team_id", "shirt_number"),
        CheckConstraint("shirt_number IS NULL OR shirt_number BETWEEN 1 AND 99", name="shirt"),
    )

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"))
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"), index=True)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"))
    kind: Mapped[MembershipKind] = mapped_column(str_enum(MembershipKind))
    status: Mapped[MembershipStatus] = mapped_column(
        str_enum(MembershipStatus), default=MembershipStatus.ACTIVE
    )
    shirt_number: Mapped[int | None] = mapped_column(Integer)
    joined_on: Mapped[date] = mapped_column(Date)
    left_on: Mapped[date | None] = mapped_column(Date)
    contract_signed: Mapped[bool] = mapped_column(Boolean, default=False)
    cnss_declared: Mapped[bool] = mapped_column(Boolean, default=False)

    person: Mapped[Person] = relationship()
    team: Mapped[Team] = relationship()
    licence: Mapped["Licence | None"] = relationship(back_populates="membership", uselist=False)


class Licence(UUIDPk, Timestamps, Base):
    """Licence numérique signée (Ed25519) — vérifiable hors connexion."""

    __tablename__ = "licences"

    number: Mapped[str] = mapped_column(String(32), unique=True)  # ex. LDS27-KAD-0001
    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("squad_memberships.id"), unique=True
    )
    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"))
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), index=True)
    status: Mapped[LicenceStatus] = mapped_column(
        str_enum(LicenceStatus), default=LicenceStatus.ACTIVE
    )
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date] = mapped_column(Date)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    issued_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    key_id: Mapped[str] = mapped_column(String(40))
    # Jeton complet contenu dans le QR : LDS1.<données>.<signature>
    token: Mapped[str] = mapped_column(Text)
    status_reason: Mapped[str | None] = mapped_column(String(255))

    membership: Mapped[SquadMembership] = relationship(back_populates="licence")
    person: Mapped[Person] = relationship()
