"""Accréditations (presse, officiels, équipes, sécurité, bénévoles, partenaires) à QR signé."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from lds_api.core.config import get_settings
from lds_api.core.errors import BusinessError, NotFound
from lds_api.domain import signed_token
from lds_api.domain.ticketing import random_code
from lds_api.models import Accreditation, Season
from lds_api.schemas import ticketing as ts
from lds_api.services import audit, licences, seasons


def _out(a: Accreditation) -> ts.AccreditationOut:
    return ts.AccreditationOut.model_validate(a, from_attributes=True)


def list_all(db: Session) -> list[ts.AccreditationOut]:
    season = seasons.current_season(db)
    rows = db.scalars(
        select(Accreditation)
        .where(Accreditation.season_id == season.id)
        .order_by(Accreditation.revoked_at.is_not(None), Accreditation.full_name)
    )
    return [_out(a) for a in rows]


def get(db: Session, acc_id: uuid.UUID) -> Accreditation:
    a = db.get(Accreditation, acc_id)
    if a is None:
        raise NotFound("Accréditation introuvable")
    return a


def create(db: Session, actor, body: ts.AccreditationIn) -> ts.AccreditationOut:
    if body.valid_until < body.valid_from:
        raise BusinessError("La fin de validité doit suivre le début")
    season: Season = seasons.current_season(db)
    zones = sorted({z.strip() for z in body.zones if z.strip()})
    a = Accreditation(
        id=uuid.uuid4(),
        season_id=season.id,
        code=random_code("A"),
        full_name=body.full_name.strip(),
        organisation=(body.organisation or "").strip() or None,
        category=body.category,
        zones=zones,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    payload = {
        "kid": get_settings().licence_key_id,
        "c": a.code,
        "nm": a.full_name,
        "cat": a.category.value,
        "z": zones,
        "vf": a.valid_from.isoformat(),
        "vu": a.valid_until.isoformat(),
        "s": season.year,
    }
    if a.organisation:
        payload["org"] = a.organisation
    a.token = signed_token.sign(
        payload, licences._signing_key(), prefix=signed_token.ACCREDITATION_PREFIX
    )
    db.add(a)
    db.flush()
    audit.record(
        db,
        actor,
        "create",
        "accreditation",
        a.id,
        {"code": a.code, "full_name": a.full_name, "category": a.category.value},
    )
    return _out(a)


def revoke(db: Session, actor, acc_id: uuid.UUID, reason: str) -> ts.AccreditationOut:
    a = get(db, acc_id)
    if a.revoked_at is not None:
        raise BusinessError("Accréditation déjà révoquée")
    a.revoked_at = datetime.now(UTC)
    audit.record(db, actor, "revoke", "accreditation", a.id, {"code": a.code, "reason": reason})
    return _out(a)
