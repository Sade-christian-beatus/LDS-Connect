"""Règles des votes du public (fonctions pures, sans base de données)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

# --- État d'un scrutin -------------------------------------------------------------
DRAFT, UPCOMING, OPEN, CLOSED = "draft", "upcoming", "open", "closed"


def effective_state(status: str, opens_at: datetime, closes_at: datetime, now: datetime) -> str:
    """Brouillon tant que l'administration ne l'a pas ouvert ; ensuite les dates décident.
    Une clôture anticipée (status « closed ») l'emporte sur les dates."""
    if status == "draft":
        return DRAFT
    if status in ("closed", "published") or now >= closes_at:
        return CLOSED
    if now < opens_at:
        return UPCOMING
    return OPEN


def results_visible(
    *,
    status: str,
    visibility: str,
    publish_at: datetime | None,
    state: str,
    now: datetime,
) -> bool:
    """Résultats publics : publiés manuellement, en continu (« immediate ») dès l'ouverture,
    ou à la date programmée."""
    if status == "published":
        return True
    if visibility == "immediate":
        return state in (OPEN, CLOSED)
    return publish_at is not None and now >= publish_at


# --- Choix du votant -----------------------------------------------------------------
class ChoiceError(ValueError):
    pass


def validate_choices(
    choices: Sequence[uuid.UUID], allowed: set[uuid.UUID], max_choices: int
) -> list[uuid.UUID]:
    if not choices:
        raise ChoiceError("Choisissez au moins une proposition")
    if len(set(choices)) != len(choices):
        raise ChoiceError("Une même proposition ne peut être choisie deux fois")
    if len(choices) > max_choices:
        raise ChoiceError(f"{max_choices} choix au maximum")
    unknown = [c for c in choices if c not in allowed]
    if unknown:
        raise ChoiceError("Proposition inconnue pour ce scrutin")
    return list(choices)


# --- Numéros autorisés ----------------------------------------------------------------
NATIONAL_LENGTH = {"226": 8}  # Burkina Faso : 8 chiffres après l'indicatif


def phone_allowed(normalized: str, country_codes: Sequence[str]) -> bool:
    """`normalized` au format +<indicatif><numéro> (voir core.crypto.normalize_phone)."""
    digits = normalized.lstrip("+")
    for code in country_codes:
        if digits.startswith(code):
            expected = NATIONAL_LENGTH.get(code)
            national = digits[len(code) :]
            return national.isdigit() and (expected is None or len(national) == expected)
    return False


# --- Détection des votes en masse -------------------------------------------------------
@dataclass(frozen=True)
class FraudRules:
    window: timedelta = timedelta(minutes=10)
    max_per_ip: int = 10  # votes d'une même adresse IP dans la fenêtre
    neighbour_span: int = 20  # numéros « voisins » : écart ≤ 20 sur le même préfixe
    max_neighbours: int = 5  # au-delà, série de numéros qui se suivent


@dataclass(frozen=True)
class RecentVote:
    phone: str  # numéro normalisé, déchiffré le temps de la vérification
    ip_hash: str | None
    cast_at: datetime


def fraud_reasons(
    *,
    phone: str,
    ip_hash: str | None,
    now: datetime,
    recent: Sequence[RecentVote],
    rules: FraudRules = FraudRules(),  # noqa: B008 — dataclass immuable
) -> list[str]:
    """Motifs de suspicion d'un nouveau vote au regard des votes récents du même scrutin.
    Un vote suspect n'est pas rejeté : il est mis de côté pour examen."""
    window = [v for v in recent if now - v.cast_at <= rules.window]
    reasons: list[str] = []
    if ip_hash and sum(v.ip_hash == ip_hash for v in window) >= rules.max_per_ip:
        reasons.append(f"plus de {rules.max_per_ip} votes depuis la même connexion en peu de temps")

    def split(p: str) -> tuple[str, int] | None:
        digits = p.lstrip("+")
        if len(digits) < 4 or not digits.isdigit():
            return None
        return digits[:-3], int(digits[-3:])

    me = split(phone)
    if me:
        prefix, tail = me
        neighbours = 0
        for v in window:
            other = split(v.phone)
            if other and other[0] == prefix and abs(other[1] - tail) <= rules.neighbour_span:
                neighbours += 1
        if neighbours >= rules.max_neighbours:
            reasons.append("série de numéros qui se suivent")
    return reasons
