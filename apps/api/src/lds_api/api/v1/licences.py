"""Licences numériques : délivrance, statut, QR code, vérification (en ligne et hors ligne)."""

import uuid
from datetime import date
from typing import Annotated

import segno
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from lds_api.core.config import get_settings
from lds_api.core.deps import Actor, DbSession, ensure_team_scope, require
from lds_api.core.errors import NotFound
from lds_api.core.rbac import Perm
from lds_api.domain.signed_token import LICENCE_PREFIX, b64url_encode
from lds_api.models import Licence, SquadMembership
from lds_api.models.enums import LicenceStatus, MembershipStatus
from lds_api.services import licences, registry, seasons

router = APIRouter(tags=["licences"])


class IssueIn(BaseModel):
    membership_id: uuid.UUID


class LicenceOut(BaseModel):
    id: uuid.UUID
    number: str
    status: LicenceStatus
    valid_from: date
    valid_until: date
    token: str


class StatusIn(BaseModel):
    status: LicenceStatus
    reason: str = Field(min_length=3, max_length=255)


class VerifyIn(BaseModel):
    token: str = Field(max_length=2000)


class VerifyOut(BaseModel):
    valid: bool
    reason: str
    status: LicenceStatus | None
    holder: dict | None


class PublicKey(BaseModel):
    kid: str
    alg: str = "Ed25519"
    x: str  # clé publique brute en base64url


class PublicKeysOut(BaseModel):
    prefix: str
    keys: list[PublicKey]


def _out(lic: Licence) -> LicenceOut:
    return LicenceOut(
        id=lic.id,
        number=lic.number,
        status=lic.status,
        valid_from=lic.valid_from,
        valid_until=lic.valid_until,
        token=lic.token,
    )


@router.get("/licences/public-keys", response_model=PublicKeysOut)
def public_keys(response: Response) -> PublicKeysOut:
    """Clés publiques de vérification : à mettre en cache sur les appareils de contrôle."""
    response.headers["Cache-Control"] = "public, max-age=3600"
    return PublicKeysOut(
        prefix=LICENCE_PREFIX,
        keys=[PublicKey(kid=k, x=b64url_encode(v)) for k, v in licences.public_keys().items()],
    )


@router.post("/admin/licences/issue", response_model=LicenceOut)
def issue(
    body: IssueIn,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.LICENCE_ISSUE))],
):
    m = db.get(SquadMembership, body.membership_id)
    if m is None:
        raise NotFound("Membre d'effectif")
    lic = licences.issue(db, actor, m)
    db.commit()
    return _out(lic)


@router.post("/admin/teams/{team_id}/licences/issue-all")
def issue_all(
    team_id: uuid.UUID,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.LICENCE_ISSUE))],
) -> dict:
    """Délivre les licences manquantes de toute une équipe."""
    season = seasons.current_season(db)
    issued, errors = 0, []
    for m in registry.active_members(db, team_id, season.id):
        if m.licence is not None:
            continue
        try:
            licences.issue(db, actor, m)
            issued += 1
        except licences.LicenceError as exc:
            errors.append({"person_id": str(m.person_id), "detail": exc.message})
    db.commit()
    return {"issued": issued, "errors": errors}


@router.post("/admin/licences/{licence_id}/status", response_model=LicenceOut)
def change_status(
    licence_id: uuid.UUID,
    body: StatusIn,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.LICENCE_STATUS))],
):
    lic = db.get(Licence, licence_id)
    if lic is None:
        raise NotFound("Licence")
    licences.set_status(db, actor, lic, body.status, body.reason)
    db.commit()
    return _out(lic)


@router.get(
    "/admin/licences/{licence_id}/qr.svg",
    response_class=Response,
    responses={200: {"content": {"image/svg+xml": {}}}},
)
def licence_qr(
    licence_id: uuid.UUID,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.SQUAD_READ))],
):
    lic = db.get(Licence, licence_id)
    if lic is None:
        raise NotFound("Licence")
    ensure_team_scope(actor, lic.membership.team_id)
    svg = segno.make(lic.token, error="m").svg_inline(scale=4, border=2)
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "no-store"})


@router.post("/licences/verify", response_model=VerifyOut)
def verify(
    body: VerifyIn,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.LICENCE_VERIFY))],
):
    result = licences.verify(db, body.token)
    holder = None
    if result.payload:
        holder = {k: result.payload.get(k) for k in ("n", "nm", "tm", "r", "no", "vu")}
    return VerifyOut(valid=result.valid, reason=result.reason, status=result.status, holder=holder)


@router.get("/licences/status-list")
def status_list(
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.LICENCE_VERIFY))],
) -> dict:
    """Licences non actives : synchronisée par les appareils pour le contrôle hors ligne."""
    season = seasons.current_season(db)
    return {
        "season": season.year,
        "key_id": get_settings().licence_key_id,
        "entries": licences.status_list(db, season.id),
    }


@router.get("/admin/teams/{team_id}/licences")
def team_licences(
    team_id: uuid.UUID,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.SQUAD_READ))],
) -> list[LicenceOut]:
    ensure_team_scope(actor, team_id)
    rows = db.scalars(
        select(Licence)
        .join(SquadMembership, SquadMembership.id == Licence.membership_id)
        .where(
            SquadMembership.team_id == team_id,
            SquadMembership.status == MembershipStatus.ACTIVE,
        )
        .order_by(Licence.number)
    )
    return [_out(lic) for lic in rows]
