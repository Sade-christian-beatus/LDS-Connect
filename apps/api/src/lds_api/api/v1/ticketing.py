"""Billetterie (public), notifications de paiement, contrôle d'accès et accréditations."""

import io
import uuid
from typing import Annotated

import segno
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from lds_api.core.deps import Actor, DbSession, client_ip, require
from lds_api.core.rbac import Perm
from lds_api.schemas import ticketing as ts
from lds_api.schemas.fixtures import MatchOut
from lds_api.services import access, accreditations
from lds_api.services import ticketing as svc

router = APIRouter(tags=["billetterie"])
TicketManager = Annotated[Actor, Depends(require(Perm.TICKET_MANAGE))]
Scanner = Annotated[Actor, Depends(require(Perm.ACCESS_SCAN))]
AccreditationManager = Annotated[Actor, Depends(require(Perm.ACCREDITATION_MANAGE))]
AccessKey = Annotated[str, Query(alias="k", min_length=8, max_length=64)]


def _svg(token: str, title: str) -> Response:
    buf = io.BytesIO()
    segno.make(token, error="m").save(
        buf, kind="svg", scale=4, border=2, xmldecl=False, svgns=True, title=title
    )
    return Response(
        buf.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"}
    )


SVG = {"response_class": Response, "responses": {200: {"content": {"image/svg+xml": {}}}}}


# --- Public -------------------------------------------------------------------------------
@router.get("/tickets/matches", response_model=list[ts.MatchTickets])
def matches_on_sale(db: DbSession):
    """Matchs à venir avec des billets en vente (ou bientôt en vente)."""
    return svc.public_matches(db)


@router.get("/tickets/matches/{match_id}", response_model=ts.MatchTickets)
def match_tickets(match_id: uuid.UUID, db: DbSession):
    return svc.match_tickets(db, match_id)


@router.post("/tickets/orders", response_model=ts.OrderCreated, status_code=201)
def create_order(body: ts.OrderIn, request: Request, db: DbSession):
    """Réserve les places 15 min et renvoie l'adresse de paiement mobile money."""
    created = svc.create_order(db, body, client_ip(request))
    db.commit()
    return created


@router.get("/tickets/orders/{reference}", response_model=ts.OrderOut)
def get_order(reference: str, k: AccessKey, db: DbSession, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return svc.order_view(db, svc.get_order(db, reference, k))


@router.get("/tickets/orders/{reference}/tickets/{code}.svg", **SVG)
def ticket_qr(reference: str, code: str, k: AccessKey, db: DbSession):
    order = svc.get_order(db, reference, k)
    return _svg(svc.ticket_token(db, order, code), code)


async def _raw_body(request: Request) -> bytes:
    """Corps brut : la signature de l'agrégateur porte sur les octets reçus, pas sur le JSON."""
    body = await request.body()
    if len(body) > 64 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Notification trop volumineuse"
        )
    return body


RawBody = Annotated[bytes, Depends(_raw_body)]


@router.post("/payments/notify", status_code=status.HTTP_204_NO_CONTENT)
def payment_notification(request: Request, db: DbSession, body: RawBody):
    """Rappel de l'agrégateur de paiement, signé (en-tête X-LDS-Signature pour le simulateur)."""
    svc.handle_notification(db, body, request.headers)
    db.commit()


# --- Administration de la billetterie -------------------------------------------------------
@router.get("/admin/ticketing/matches", response_model=list[MatchOut])
def ticketing_matches(db: DbSession, actor: TicketManager):
    return svc.current_matches(db)


@router.get("/admin/ticket-types", response_model=list[ts.TicketTypeAdminOut])
def list_types(match_id: uuid.UUID, db: DbSession, actor: TicketManager):
    return svc.admin_types(db, match_id)


@router.post("/admin/ticket-types", response_model=ts.TicketTypeAdminOut, status_code=201)
def create_type(body: ts.TicketTypeIn, db: DbSession, actor: TicketManager):
    out = svc.create_type(db, actor, body)
    db.commit()
    return out


@router.patch("/admin/ticket-types/{type_id}", response_model=ts.TicketTypeAdminOut)
def update_type(type_id: uuid.UUID, body: ts.TicketTypeUpdate, db: DbSession, actor: TicketManager):
    out = svc.update_type(db, actor, type_id, body)
    db.commit()
    return out


@router.get("/admin/orders", response_model=list[ts.OrderAdminOut])
def list_orders(
    match_id: uuid.UUID,
    db: DbSession,
    actor: TicketManager,
    state: Annotated[str | None, Query(description="pending | paid | failed | expired…")] = None,
):
    return svc.admin_orders(db, match_id, state)


@router.post("/admin/orders/{reference}/refund", status_code=status.HTTP_204_NO_CONTENT)
def refund_order(reference: str, body: ts.RefundIn, db: DbSession, actor: TicketManager):
    svc.mark_refunded(db, actor, reference, body.reason, body.transaction)
    db.commit()


@router.post("/admin/tickets/{code}/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_ticket(code: str, body: ts.CancelIn, db: DbSession, actor: TicketManager):
    svc.cancel_ticket(db, actor, code, body.reason)
    db.commit()


# --- Contrôle d'accès -----------------------------------------------------------------------
@router.get("/access/matches", response_model=list[MatchOut])
def access_matches(db: DbSession, actor: Scanner):
    """Matchs à venir de la saison, pour préparer un appareil de contrôle."""
    return svc.current_matches(db)


@router.get("/access/matches/{match_id}/manifest", response_model=ts.Manifest)
def access_manifest(match_id: uuid.UUID, db: DbSession, actor: Scanner, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return access.manifest(db, match_id)


@router.post("/access/scans", response_model=list[ts.ScanOut])
def access_scans(body: ts.ScanBatch, db: DbSession, actor: Scanner):
    """Enregistre des passages (un seul en ligne, ou un lot synchronisé après coupure)."""
    out = access.record(db, actor, body.scans)
    db.commit()
    return out


@router.get("/access/matches/{match_id}/stats", response_model=ts.AccessStats)
def access_stats(match_id: uuid.UUID, db: DbSession, actor: Scanner):
    return access.stats(db, match_id)


# --- Accréditations -------------------------------------------------------------------------
class RevokeIn(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


@router.get("/admin/accreditations", response_model=list[ts.AccreditationOut])
def list_accreditations(db: DbSession, actor: AccreditationManager):
    return accreditations.list_all(db)


@router.post("/admin/accreditations", response_model=ts.AccreditationOut, status_code=201)
def create_accreditation(body: ts.AccreditationIn, db: DbSession, actor: AccreditationManager):
    out = accreditations.create(db, actor, body)
    db.commit()
    return out


@router.post("/admin/accreditations/{acc_id}/revoke", response_model=ts.AccreditationOut)
def revoke_accreditation(
    acc_id: uuid.UUID, body: RevokeIn, db: DbSession, actor: AccreditationManager
):
    out = accreditations.revoke(db, actor, acc_id, body.reason)
    db.commit()
    return out


@router.get("/admin/accreditations/{acc_id}/qr.svg", **SVG)
def accreditation_qr(acc_id: uuid.UUID, db: DbSession, actor: AccreditationManager):
    a = accreditations.get(db, acc_id)
    return _svg(a.token, a.code)
