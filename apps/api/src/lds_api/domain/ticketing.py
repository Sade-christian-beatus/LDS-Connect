"""Règles de billetterie et de contrôle d'accès (fonctions pures, sans base de données)."""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

# Codes lisibles à l'oral et sur papier : ni 0/O, ni 1/I/L
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

RESERVATION_TTL = timedelta(minutes=15)

# États de vente d'une catégorie de billets
NOT_OPEN = "not_open"
ON_SALE = "on_sale"
SOLD_OUT = "sold_out"
CLOSED = "closed"


def random_code(prefix: str, length: int = 8) -> str:
    """Ex. « B-7KQ2M9XA » : 31^8 ≈ 850 milliards de combinaisons, impossible à deviner."""
    return f"{prefix}-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


def remaining(quota: int | None, taken: int) -> int | None:
    """Places restantes (None = sans limite). `taken` = billets émis + places réservées."""
    return None if quota is None else max(quota - taken, 0)


def sale_state(
    *,
    is_active: bool,
    opens_at: datetime | None,
    closes_at: datetime | None,
    kickoff_at: datetime | None,
    left: int | None,
    now: datetime,
) -> str:
    """Les ventes ferment à la date choisie, sinon au coup d'envoi."""
    if not is_active:
        return CLOSED
    if opens_at and now < opens_at:
        return NOT_OPEN
    end = closes_at or kickoff_at
    if end and now >= end:
        return CLOSED
    if left is not None and left <= 0:
        return SOLD_OUT
    return ON_SALE


class OrderError(ValueError):
    pass


def check_quantity(quantity: int, *, max_per_order: int, left: int | None) -> None:
    if quantity < 1:
        raise OrderError("Choisissez au moins un billet")
    if quantity > max_per_order:
        raise OrderError(f"{max_per_order} billets au maximum par commande")
    if left is not None and quantity > left:
        raise OrderError(
            "Plus assez de places disponibles"
            if left
            else "Complet : il n'y a plus de places dans cette catégorie"
        )


# --- Contrôle d'accès -------------------------------------------------------------------
@dataclass(frozen=True)
class PriorEntry:
    scanned_at: datetime
    device: str | None


@dataclass(frozen=True)
class Decision:
    result: str  # valeur de models.enums.ScanResult
    detail: str


def decide_ticket(
    *,
    ticket_status: str,
    ticket_match_id: object,
    scan_match_id: object | None,
    first_entry: PriorEntry | None,
    scanned_at: datetime,
) -> Decision:
    """Décision pour un billet authentique (signature déjà vérifiée).

    Entre deux appareils hors ligne qui ont admis le même billet, le premier passage
    (heure de l'appareil) reste l'entrée ; le suivant est enregistré comme double entrée.
    """
    if ticket_status == "cancelled":
        return Decision("invalid", "Billet annulé")
    if scan_match_id is not None and ticket_match_id != scan_match_id:
        return Decision("wrong_match", "Billet valable pour un autre match")
    if first_entry is not None and first_entry.scanned_at <= scanned_at:
        at = first_entry.scanned_at.strftime("%H:%M")
        where = f" ({first_entry.device})" if first_entry.device else ""
        return Decision("duplicate", f"Déjà entré à {at}{where}")
    return Decision("admitted", "Entrée autorisée")


# --- Zones du stade (audit M10) --------------------------------------------------------------
# Une porte sans zone est une entrée du public (tribunes) : billets et accréditations y passent.
# Une porte attachée à une zone réservée (pelouse, vestiaires, presse…) n'admet que les
# accréditations qui portent cette zone, ou « Toutes zones ».
ALL_ZONES = "Toutes zones"


def zone_refusal(*, kind: str, gate_zone: str | None, zones: list[str] | None = None) -> str | None:
    """Motif de refus lié à la zone, ou None si le passage est permis à cette porte."""
    if not gate_zone:
        return None
    if kind == "ticket":
        return f"Billet du public : pas d'accès à la zone « {gate_zone} »"
    if ALL_ZONES in (zones or []) or gate_zone in (zones or []):
        return None
    return f"Zone « {gate_zone} » non autorisée pour cette accréditation"
