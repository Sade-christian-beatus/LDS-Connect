"""Phase 2 — billetterie et accréditations (squelette du modèle, logique à développer)."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from lds_api.db.base import Base, Timestamps, UUIDPk
from lds_api.db.types import EncryptedString
from lds_api.models.enums import (
    AccreditationCategory,
    OrderKind,
    OrderStatus,
    TicketStatus,
    str_enum,
)


class TicketType(UUIDPk, Timestamps, Base):
    __tablename__ = "ticket_types"

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"))
    match_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("matches.id"))
    name: Mapped[str] = mapped_column(String(80))  # Pelouse, Tribune, Forfait supporter…
    price_fcfa: Mapped[int] = mapped_column(Integer)
    quota: Mapped[int | None] = mapped_column(Integer)
    sales_open_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sales_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Order(UUIDPk, Timestamps, Base):
    """Commande payée via un agrégateur mobile money (interface PaymentProvider)."""

    __tablename__ = "orders"

    reference: Mapped[str] = mapped_column(String(40), unique=True)
    kind: Mapped[OrderKind] = mapped_column(str_enum(OrderKind))
    status: Mapped[OrderStatus] = mapped_column(str_enum(OrderStatus), default=OrderStatus.PENDING)
    amount_fcfa: Mapped[int] = mapped_column(Integer)
    phone: Mapped[str | None] = mapped_column(EncryptedString)
    phone_index: Mapped[str | None] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    provider_reference: Mapped[str | None] = mapped_column(String(120), index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_callback: Mapped[dict | None] = mapped_column(JSONB)


class Ticket(UUIDPk, Timestamps, Base):
    __tablename__ = "tickets"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ticket_types.id"))
    match_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("matches.id"), index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    token: Mapped[str] = mapped_column(Text)  # QR signé
    status: Mapped[TicketStatus] = mapped_column(str_enum(TicketStatus), default=TicketStatus.VALID)
    holder_name: Mapped[str | None] = mapped_column(String(120))
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scanned_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    scan_device: Mapped[str | None] = mapped_column(String(80))


class Accreditation(UUIDPk, Timestamps, Base):
    __tablename__ = "accreditations"

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"))
    code: Mapped[str] = mapped_column(String(32), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    organisation: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[AccreditationCategory] = mapped_column(str_enum(AccreditationCategory))
    zones: Mapped[list[str]] = mapped_column(JSONB, default=list)
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date] = mapped_column(Date)
    token: Mapped[str] = mapped_column(Text)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
