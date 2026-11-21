"""Délivrance, changement de statut et vérification des licences numériques."""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lds_api.core.config import get_settings
from lds_api.core.errors import BusinessError
from lds_api.domain import signed_token
from lds_api.domain.eligibility import age_on
from lds_api.models import CompetitionRules, Licence, Season, SquadMembership
from lds_api.models.enums import LicenceStatus, MembershipKind, MembershipStatus
from lds_api.services import audit


class LicenceError(BusinessError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="licence")


@lru_cache
def _signing_key():
    raw = get_settings().licence_signing_key.get_secret_value()
    if not raw:
        raise LicenceError("LICENCE_SIGNING_KEY n'est pas configurée (voir `make keys`).")
    return signed_token.load_private_key(raw)


def public_keys() -> dict[str, bytes]:
    """Clés publiques acceptées : clé courante + anciennes clés déclarées (rotation)."""
    s = get_settings()
    keys = {s.licence_key_id: signed_token.public_key_raw(_signing_key())}
    for item in filter(None, (x.strip() for x in s.licence_previous_public_keys.split(","))):
        kid, _, b64 = item.partition(":")
        keys[kid] = signed_token.b64url_decode(b64)
    return keys


def _next_number(db: Session, season: Season) -> str:
    prefix = f"LDS{season.year % 100:02d}-"
    count = db.scalar(select(func.count(Licence.id)).where(Licence.season_id == season.id)) or 0
    return f"{prefix}{count + 1:05d}"


def build_payload(lic: Licence, m: SquadMembership, season: Season) -> dict:
    """Données publiées dans le QR : le strict nécessaire au contrôle d'identité au stade.
    Ni date de naissance, ni CNIB, ni téléphone (voir docs/DONNEES_PERSONNELLES.md)."""
    p = m.person
    payload = {
        "kid": lic.key_id,
        "n": lic.number,
        "s": season.year,
        "nm": f"{p.first_name} {p.last_name}",
        "tm": m.team.short_name,
        "r": "J" if m.kind == MembershipKind.PLAYER else "E",
        "vf": lic.valid_from.isoformat(),
        "vu": lic.valid_until.isoformat(),
    }
    if m.shirt_number:
        payload["no"] = m.shirt_number
    return payload


def issue(db: Session, actor, membership: SquadMembership) -> Licence:
    """Délivre (ou ré-émet) la licence d'un membre d'effectif."""
    if membership.status != MembershipStatus.ACTIVE:
        raise LicenceError("Ce membre ne fait plus partie de l'effectif")
    season = db.get(Season, membership.season_id)
    rules = db.scalar(select(CompetitionRules).where(CompetitionRules.season_id == season.id))
    if membership.kind == MembershipKind.PLAYER:
        ref = rules.age_reference_date or season.starts_on
        if age_on(membership.person.birth_date, ref) < rules.min_age:
            raise LicenceError(f"Âge minimum non atteint ({rules.min_age} ans)")

    lic = membership.licence
    created = lic is None
    if created:
        lic = Licence(
            number=_next_number(db, season),
            membership_id=membership.id,
            season_id=season.id,
            person_id=membership.person_id,
        )
        db.add(lic)
    elif lic.status == LicenceStatus.REVOKED:
        raise LicenceError("Licence révoquée : une nouvelle décision est nécessaire")

    lic.status = LicenceStatus.ACTIVE
    lic.status_reason = None
    lic.valid_from = max(season.starts_on, membership.joined_on)
    lic.valid_until = season.ends_on
    lic.issued_at = datetime.now(UTC)
    lic.issued_by_id = getattr(actor, "id", None)
    lic.key_id = get_settings().licence_key_id
    lic.token = signed_token.sign(
        build_payload(lic, membership, season),
        _signing_key(),
        prefix=signed_token.LICENCE_PREFIX,
    )
    db.flush()
    audit.record(
        db,
        actor,
        "issue" if created else "reissue",
        "licence",
        lic.id,
        {"number": lic.number, "person_id": lic.person_id},
    )
    return lic


def set_status(db: Session, actor, lic: Licence, status: LicenceStatus, reason: str) -> Licence:
    if lic.status == LicenceStatus.REVOKED:
        raise LicenceError("Une licence révoquée ne peut plus changer de statut")
    before = lic.status
    lic.status = status
    lic.status_reason = reason
    audit.record(
        db,
        actor,
        "status_change",
        "licence",
        lic.id,
        {"status": [before, status], "reason": reason},
    )
    return lic


@dataclass
class Verification:
    valid: bool
    reason: str
    payload: dict | None = None
    status: LicenceStatus | None = None


def verify(db: Session, token: str, *, on: date | None = None) -> Verification:
    """Vérification en ligne : signature, validité temporelle et statut en base."""
    on = on or date.today()
    try:
        payload = signed_token.verify(token, public_keys(), prefix=signed_token.LICENCE_PREFIX)
    except signed_token.TokenError as exc:
        return Verification(False, str(exc))
    lic = db.scalar(select(Licence).where(Licence.number == payload.get("n")))
    if lic is None or lic.token != token.strip():
        return Verification(False, "Licence inconnue ou remplacée", payload)
    if lic.status != LicenceStatus.ACTIVE:
        return Verification(False, f"Licence {lic.status.value}", payload, lic.status)
    if on < lic.valid_from:
        msg = f"Licence pas encore valide (à partir du {lic.valid_from:%d/%m/%Y})"
        return Verification(False, msg, payload, lic.status)
    if on > lic.valid_until:
        return Verification(False, "Licence expirée", payload, lic.status)
    return Verification(True, "Licence valide", payload, lic.status)


def status_list(db: Session, season_id: uuid.UUID) -> list[dict]:
    """Licences non actives, pour le cache des appareils de contrôle hors ligne."""
    rows = db.scalars(
        select(Licence).where(
            Licence.season_id == season_id, Licence.status != LicenceStatus.ACTIVE
        )
    )
    return [
        {"n": lic.number, "status": lic.status.value, "updated_at": lic.updated_at.isoformat()}
        for lic in rows
    ]
