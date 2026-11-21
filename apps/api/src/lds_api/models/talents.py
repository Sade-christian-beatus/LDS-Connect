"""Phase 3 — statistiques individuelles (squelette, agrégées depuis les feuilles validées)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from lds_api.db.base import Base, UUIDPk


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
