"""Phase 2 — votes du public (squelette du modèle, logique à développer).

Principes : un vote par numéro de téléphone et par scrutin (unicité sur l'index aveugle),
vérification par OTP SMS, journal complet, détection des votes en masse.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lds_api.db.base import Base, Timestamps, UUIDPk
from lds_api.db.types import EncryptedString
from lds_api.models.enums import (
    BallotKind,
    BallotStatus,
    ResultsVisibility,
    VoteStatus,
    str_enum,
)


class Ballot(UUIDPk, Timestamps, Base):
    """Scrutin (homme du match, but du mois, joueur de la saison…)."""

    __tablename__ = "ballots"

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"))
    kind: Mapped[BallotKind] = mapped_column(str_enum(BallotKind))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    match_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("matches.id"))
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[BallotStatus] = mapped_column(str_enum(BallotStatus), default=BallotStatus.DRAFT)
    results_visibility: Mapped[ResultsVisibility] = mapped_column(
        str_enum(ResultsVisibility), default=ResultsVisibility.IMMEDIATE
    )
    results_publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Nombre de choix par votant (ex. 11 pour l'onze idéal)
    max_choices: Mapped[int] = mapped_column(Integer, default=1)
    # Vote payant par mobile money : désactivé par défaut
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    price_fcfa: Mapped[int | None] = mapped_column(Integer)

    options: Mapped[list["BallotOption"]] = relationship(back_populates="ballot")


class BallotOption(UUIDPk, Base):
    __tablename__ = "ballot_options"

    ballot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ballots.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(160))
    person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("persons.id"))
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"))
    match_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("match_events.id"))
    media_url: Mapped[str | None] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0)

    ballot: Mapped[Ballot] = relationship(back_populates="options")


class OtpChallenge(UUIDPk, Base):
    __tablename__ = "otp_challenges"

    phone_index: Mapped[str] = mapped_column(String(64), index=True)
    phone: Mapped[str] = mapped_column(EncryptedString)
    purpose: Mapped[str] = mapped_column(String(40))  # vote, …
    code_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_hash: Mapped[str | None] = mapped_column(String(64))


class Vote(UUIDPk, Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("ballot_id", "phone_index", "option_id"),)

    ballot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ballots.id"), index=True)
    option_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ballot_options.id"))
    phone_index: Mapped[str] = mapped_column(String(64), index=True)
    otp_challenge_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("otp_challenges.id"))
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"))
    cast_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[VoteStatus] = mapped_column(str_enum(VoteStatus), default=VoteStatus.VALID)
    flag_reason: Mapped[str | None] = mapped_column(String(160))
