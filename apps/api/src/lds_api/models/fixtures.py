"""Stades et matchs."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lds_api.db.base import Base, Timestamps, UUIDPk
from lds_api.models.enums import MatchPhase, MatchStatus, str_enum
from lds_api.models.registry import Pool, Team


class Venue(UUIDPk, Timestamps, Base):
    __tablename__ = "venues"

    name: Mapped[str] = mapped_column(String(120), unique=True)
    city: Mapped[str] = mapped_column(String(80))
    capacity: Mapped[int | None] = mapped_column(Integer)
    address: Mapped[str | None] = mapped_column(String(255))
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)


class Match(UUIDPk, Timestamps, Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("home_team_id IS NULL OR home_team_id <> away_team_id", name="distinct"),
    )

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"), index=True)
    phase: Mapped[MatchPhase] = mapped_column(str_enum(MatchPhase))
    pool_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pools.id"), index=True)
    round_number: Mapped[int | None] = mapped_column(Integer)  # journée (poules)
    # Phases finales : identifiant de case (QF1…QF4, SF1, SF2, F, P3)
    bracket_slot: Mapped[str | None] = mapped_column(String(8))
    # Nul tant que l'équipe d'une phase finale n'est pas connue
    home_team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"))
    venue_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("venues.id"))
    kickoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[MatchStatus] = mapped_column(
        str_enum(MatchStatus), default=MatchStatus.SCHEDULED
    )
    # Score officiel, recopié depuis la feuille de match validée
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    home_penalties: Mapped[int | None] = mapped_column(Integer)
    away_penalties: Mapped[int | None] = mapped_column(Integer)
    winner_team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"))
    # Score en direct (non officiel) pendant le match
    live_minute: Mapped[int | None] = mapped_column(Integer)

    pool: Mapped[Pool | None] = relationship()
    venue: Mapped[Venue | None] = relationship()
    home_team: Mapped[Team | None] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team | None] = relationship(foreign_keys=[away_team_id])
