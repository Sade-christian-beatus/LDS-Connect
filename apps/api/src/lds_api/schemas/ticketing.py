"""Schémas de la billetterie, du contrôle d'accès et des accréditations."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from lds_api.models.enums import AccreditationCategory, ScanResult, TicketStatus
from lds_api.schemas.fixtures import MatchOut

SaleState = Literal["not_open", "on_sale", "sold_out", "closed"]
OrderState = Literal["pending", "paid", "failed", "cancelled", "refunded", "expired"]


# --- Catégories de billets ----------------------------------------------------------------
class TicketTypeOut(BaseModel):
    id: uuid.UUID
    match_id: uuid.UUID
    name: str
    description: str | None
    price_fcfa: int
    quota: int | None
    remaining: int | None
    max_per_order: int
    sales_open_at: datetime | None
    sales_close_at: datetime | None
    is_active: bool
    state: SaleState


class TicketTypeAdminOut(TicketTypeOut):
    sold: int  # billets émis (hors annulés)
    reserved: int  # places réservées par des commandes en attente de paiement
    revenue_fcfa: int


class TicketTypeIn(BaseModel):
    match_id: uuid.UUID
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    price_fcfa: int = Field(ge=0, le=1_000_000)
    quota: int | None = Field(default=None, ge=1, le=200_000)
    max_per_order: int = Field(default=10, ge=1, le=50)
    sales_open_at: datetime | None = None
    sales_close_at: datetime | None = None


class TicketTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    price_fcfa: int | None = Field(default=None, ge=0, le=1_000_000)
    quota: int | None = Field(default=None, ge=1, le=200_000)
    max_per_order: int | None = Field(default=None, ge=1, le=50)
    sales_open_at: datetime | None = None
    sales_close_at: datetime | None = None
    is_active: bool | None = None


class MatchTickets(BaseModel):
    match: MatchOut
    types: list[TicketTypeOut]


# --- Commandes (sans compte) ----------------------------------------------------------------
class OrderIn(BaseModel):
    ticket_type_id: uuid.UUID
    quantity: int = Field(ge=1, le=50)
    buyer_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=30)


class OrderCreated(BaseModel):
    reference: str
    access_key: str  # à conserver : donne accès aux billets (lien envoyé aussi par SMS)
    checkout_url: str
    expires_at: datetime
    amount_fcfa: int


class TicketOut(BaseModel):
    code: str
    token: str
    status: TicketStatus
    type_name: str
    scanned_at: datetime | None


class OrderOut(BaseModel):
    reference: str
    state: OrderState
    amount_fcfa: int
    quantity: int
    buyer_name: str
    phone_hint: str
    type_name: str
    match: MatchOut
    expires_at: datetime | None
    paid_at: datetime | None
    tickets: list[TicketOut]


class OrderAdminOut(BaseModel):
    reference: str
    state: OrderState
    amount_fcfa: int
    quantity: int
    buyer_name: str
    phone_hint: str
    type_name: str
    created_at: datetime
    paid_at: datetime | None
    provider: str
    tickets: list[str]


class CancelIn(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


# --- Contrôle d'accès -----------------------------------------------------------------------
class ManifestTicket(BaseModel):
    c: str  # code du billet
    s: TicketStatus
    t: str  # catégorie
    e: datetime | None = None  # entrée déjà enregistrée


class Manifest(BaseModel):
    """Ce qu'un appareil de contrôle télécharge avant le match pour travailler hors ligne."""

    match: MatchOut
    generated_at: datetime
    tickets: list[ManifestTicket]
    revoked_accreditations: list[str]


class ScanIn(BaseModel):
    client_id: uuid.UUID  # identifiant généré par l'appareil : renvoi sans doublon
    token: str = Field(max_length=2000)
    match_id: uuid.UUID | None = None
    scanned_at: datetime
    offline: bool = False
    device: str | None = Field(default=None, max_length=80)
    # Zone gardée par l'appareil (vide : entrée du public)
    zone: str | None = Field(default=None, max_length=40)


class ScanBatch(BaseModel):
    scans: list[ScanIn] = Field(max_length=500)


class ScanOut(BaseModel):
    client_id: uuid.UUID
    result: ScanResult
    detail: str
    kind: Literal["ticket", "accreditation", "unknown"]
    code: str | None
    label: str | None  # catégorie du billet ou nom de l'accrédité


class AccessStats(BaseModel):
    match_id: uuid.UUID
    tickets_sold: int
    admitted: int
    duplicates: int
    invalid: int
    accreditations_admitted: int
    by_device: dict[str, int]


# --- Accréditations -------------------------------------------------------------------------
class AccreditationIn(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    organisation: str | None = Field(default=None, max_length=120)
    category: AccreditationCategory
    zones: list[str] = Field(default_factory=list, max_length=10)
    valid_from: date
    valid_until: date


class AccreditationOut(BaseModel):
    id: uuid.UUID
    code: str
    full_name: str
    organisation: str | None
    category: AccreditationCategory
    zones: list[str]
    valid_from: date
    valid_until: date
    token: str
    revoked_at: datetime | None
