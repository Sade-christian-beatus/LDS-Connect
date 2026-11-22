"""Phase 2 — billetterie, contrôle d'accès et accréditations."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from lds_api.db.base import Base, Timestamps, UUIDPk
from lds_api.db.types import EncryptedString
from lds_api.models.enums import (
    AccreditationCategory,
    OrderKind,
    OrderStatus,
    ScanResult,
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
    description: Mapped[str | None] = mapped_column(String(255))
    max_per_order: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


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
    # Billetterie (commande sans compte)
    ticket_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ticket_types.id"), index=True
    )
    quantity: Mapped[int | None] = mapped_column(Integer)
    buyer_name: Mapped[str | None] = mapped_column(String(120))
    # Places réservées jusqu'à cette heure tant que le paiement n'est pas confirmé
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Empreinte de la clé du lien « mes billets » (la clé n'est jamais stockée en clair)
    access_key_hash: Mapped[str | None] = mapped_column(String(64))


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


class AccessScan(UUIDPk, Timestamps, Base):
    """Passage au contrôle d'accès (billet ou accréditation), y compris scanné hors ligne
    puis synchronisé : `client_id` rend l'envoi idempotent, `scanned_at` est l'heure de
    l'appareil, qui départage deux appareils ayant admis le même billet."""

    __tablename__ = "access_scans"

    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    match_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("matches.id"), index=True)
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tickets.id"), index=True)
    accreditation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accreditations.id"), index=True
    )
    code: Mapped[str | None] = mapped_column(String(32))
    result: Mapped[ScanResult] = mapped_column(str_enum(ScanResult))
    detail: Mapped[str | None] = mapped_column(String(255))
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    offline: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    device: Mapped[str | None] = mapped_column(String(80))
    scanned_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
