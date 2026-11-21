"""Feuille de match numérique : composition et événements."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lds_api.db.base import Base, Timestamps, UUIDPk
from lds_api.models.enums import EventType, LineupRole, SheetStatus, str_enum
from lds_api.models.fixtures import Match
from lds_api.models.registry import Person


class MatchSheet(UUIDPk, Timestamps, Base):
    """Cycle de vie : brouillon → soumise → validée → clôturée."""

    __tablename__ = "match_sheets"

    match_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matches.id"), unique=True)
    status: Mapped[SheetStatus] = mapped_column(str_enum(SheetStatus), default=SheetStatus.DRAFT)
    delegate_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    referee_name: Mapped[str | None] = mapped_column(String(120))
    assistant_referees: Mapped[str | None] = mapped_column(String(255))
    attendance: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validated_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Verrou optimiste : incrémenté à chaque modification (synchronisation hors ligne)
    version: Mapped[int] = mapped_column(Integer, default=1)

    match: Mapped[Match] = relationship()
    lineup: Mapped[list["LineupEntry"]] = relationship(
        back_populates="sheet", cascade="all, delete-orphan"
    )
    events: Mapped[list["MatchEvent"]] = relationship(
        back_populates="sheet", cascade="all, delete-orphan", order_by="MatchEvent.minute"
    )


class LineupEntry(UUIDPk, Base):
    __tablename__ = "lineup_entries"
    __table_args__ = (UniqueConstraint("sheet_id", "person_id"),)

    sheet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("match_sheets.id", ondelete="CASCADE"))
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"))
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"))
    licence_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("licences.id"))
    role: Mapped[LineupRole] = mapped_column(str_enum(LineupRole))
    shirt_number: Mapped[int | None] = mapped_column(Integer)
    is_captain: Mapped[bool] = mapped_column(Boolean, default=False)
    is_goalkeeper: Mapped[bool] = mapped_column(Boolean, default=False)
    # Instantané du statut « local » au moment de la composition (preuve en cas de réclamation)
    is_local_snapshot: Mapped[bool] = mapped_column(Boolean, default=False)

    sheet: Mapped[MatchSheet] = relationship(back_populates="lineup")
    person: Mapped[Person] = relationship()


class MatchEvent(UUIDPk, Timestamps, Base):
    __tablename__ = "match_events"
    __table_args__ = (
        CheckConstraint("minute BETWEEN 0 AND 130", name="minute"),
        CheckConstraint("added_time IS NULL OR added_time BETWEEN 0 AND 30", name="added"),
    )

    sheet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("match_sheets.id", ondelete="CASCADE"), index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"))
    type: Mapped[EventType] = mapped_column(str_enum(EventType))
    minute: Mapped[int] = mapped_column(Integer)
    added_time: Mapped[int | None] = mapped_column(Integer)
    # Buteur, joueur averti, ou joueur sortant (remplacement)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"))
    # Passeur décisif, ou joueur entrant (remplacement)
    related_person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("persons.id"))
    # Identifiant généré par le client : rejouer une action hors ligne ne crée pas de doublon
    client_uuid: Mapped[uuid.UUID | None] = mapped_column(unique=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    sheet: Mapped[MatchSheet] = relationship(back_populates="events")
    person: Mapped[Person] = relationship(foreign_keys=[person_id])
    related_person: Mapped[Person | None] = relationship(foreign_keys=[related_person_id])
