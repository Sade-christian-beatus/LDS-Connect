"""Phase 3 — talents : statistiques individuelles (recalculées depuis les feuilles validées),
liste de suivi et notes d'observation de la cellule technique (internes, chiffrées)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from lds_api.db.base import Base, Timestamps, UUIDPk
from lds_api.db.types import EncryptedString


class PlayerStat(UUIDPk, Base):
    __tablename__ = "player_stats"
    __table_args__ = (UniqueConstraint("season_id", "person_id", "team_id"),)

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"))
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"))
    appearances: Mapped[int] = mapped_column(Integer, default=0)
    starts: Mapped[int] = mapped_column(Integer, default=0)
    minutes_played: Mapped[int] = mapped_column(Integer, default=0)
    goals: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0)
    red_cards: Mapped[int] = mapped_column(Integer, default=0)
    clean_sheets: Mapped[int] = mapped_column(Integer, default=0)
    man_of_the_match: Mapped[int] = mapped_column(Integer, default=0)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TalentWatch(UUIDPk, Timestamps, Base):
    """Joueur suivi par la cellule technique (liste de suivi interne)."""

    __tablename__ = "talent_watch"

    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), unique=True)
    added_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    # Étiquettes libres : « potentiel sélection », « à revoir en match »…
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)


class TalentNote(UUIDPk, Base):
    """Note d'observation : strictement interne, texte chiffré, lecture journalisée."""

    __tablename__ = "talent_notes"
    __table_args__ = (CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="rating"),)

    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), index=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    match_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("matches.id"))
    rating: Mapped[int | None] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(EncryptedString)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Rien n'est effacé : une note retirée reste dans l'historique (journal d'audit)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_reason: Mapped[str | None] = mapped_column(String(255))
