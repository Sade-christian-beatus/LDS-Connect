"""Suspensions (automatiques par cartons ou décidées par la commission)."""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from lds_api.db.base import Base, Timestamps, UUIDPk
from lds_api.models.enums import SuspensionReason, SuspensionStatus, str_enum


class Suspension(UUIDPk, Timestamps, Base):
    __tablename__ = "suspensions"

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"))
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"))
    reason: Mapped[SuspensionReason] = mapped_column(str_enum(SuspensionReason))
    source_match_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("matches.id"))
    matches_count: Mapped[int] = mapped_column(Integer, default=1)
    matches_served: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[SuspensionStatus] = mapped_column(
        str_enum(SuspensionStatus), default=SuspensionStatus.ACTIVE
    )
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    reference: Mapped[str | None] = mapped_column(String(60))  # n° de décision
