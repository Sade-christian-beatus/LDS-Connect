"""Billetterie : catégories de billets, commandes sans compte, paiement, émission des billets.

Parcours d'achat : le supporter choisit une catégorie et une quantité, donne son nom et son
numéro ; les places sont réservées 15 min pendant le paiement mobile money (agrégateur
derrière `PaymentProvider`). À la notification de paiement, les billets sont émis avec un
QR signé (Ed25519, comme les licences) et un lien « mes billets » est envoyé par SMS. Ce lien
porte une clé secrète dont seule l'empreinte est conservée en base.
"""

import hashlib
import hmac
import json
import logging
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lds_api.core import ratelimit
from lds_api.core.config import get_settings
from lds_api.core.crypto import _blind_key, mask_phone, normalize_phone, phone_index
from lds_api.core.errors import BusinessError, NotFound
from lds_api.domain import signed_token
from lds_api.domain import ticketing as rules
from lds_api.domain.voting import phone_allowed
from lds_api.models import Match, Order, Season, Ticket, TicketType
from lds_api.models.enums import MatchStatus, OrderKind, OrderStatus, TicketStatus
from lds_api.providers.payment import InvalidSignature, PaymentDisabled, get_payment_provider
from lds_api.providers.sms import get_sms_provider
from lds_api.schemas import ticketing as ts
from lds_api.services import audit, fixtures, licences, seasons

log = logging.getLogger(__name__)

ORDERS_PER_PHONE = (5, 900)  # 5 commandes par numéro par quart d'heure
ORDERS_PER_IP = (20, 3600)


def now() -> datetime:
    return datetime.now(UTC)


def _key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _access_key(reference: str) -> str:
    """Clé du lien « mes billets », dérivée d'un secret serveur : la même dans le navigateur
    de l'acheteur et dans le SMS, sans jamais être stockée en clair."""
    mac = hmac.new(_blind_key(), f"order-access:{reference}".encode(), hashlib.sha256).digest()
    return signed_token.b64url_encode(mac)[:24]


# --- Disponibilités -----------------------------------------------------------------------
def _counts(db: Session, tt_id: uuid.UUID, at: datetime, *, exclude_order=None) -> tuple[int, int]:
    """(billets émis hors annulés, places réservées par des commandes en attente)."""
    sold = db.scalar(
        select(func.count(Ticket.id)).where(
            Ticket.ticket_type_id == tt_id, Ticket.status != TicketStatus.CANCELLED
        )
    )
    q = select(func.coalesce(func.sum(Order.quantity), 0)).where(
        Order.ticket_type_id == tt_id,
        Order.status == OrderStatus.PENDING,
        Order.expires_at > at,
    )
    if exclude_order is not None:
        q = q.where(Order.id != exclude_order)
    return sold or 0, db.scalar(q) or 0


def _view(db: Session, tt: TicketType, match: Match, at: datetime, *, admin=False):
    sold, reserved = _counts(db, tt.id, at)
    left = rules.remaining(tt.quota, sold + reserved)
    state = rules.sale_state(
        is_active=tt.is_active,
        opens_at=tt.sales_open_at,
        closes_at=tt.sales_close_at,
        kickoff_at=match.kickoff_at,
        left=left,
        now=at,
    )
    data = {
        "id": tt.id,
        "match_id": tt.match_id,
        "name": tt.name,
        "description": tt.description,
        "price_fcfa": tt.price_fcfa,
        "quota": tt.quota,
        "remaining": left,
        "max_per_order": tt.max_per_order,
        "sales_open_at": tt.sales_open_at,
        "sales_close_at": tt.sales_close_at,
        "is_active": tt.is_active,
        "state": state,
    }
    if not admin:
        return ts.TicketTypeOut(**data)
    return ts.TicketTypeAdminOut(
        **data, sold=sold, reserved=reserved, revenue_fcfa=sold * tt.price_fcfa
    )


def _match(db: Session, match_id: uuid.UUID) -> Match:
    m = db.scalar(fixtures.match_query().where(Match.id == match_id))
    if m is None:
        raise NotFound("Match introuvable")
    return m


def _types(db: Session, match_id: uuid.UUID, *, active_only: bool) -> list[TicketType]:
    q = select(TicketType).where(TicketType.match_id == match_id)
    if active_only:
        q = q.where(TicketType.is_active.is_(True))
    return list(db.scalars(q.order_by(TicketType.price_fcfa, TicketType.name)))


def public_matches(db: Session) -> list[ts.MatchTickets]:
    """Matchs à venir pour lesquels des billets sont (ou seront) en vente."""
    at = now()
    match_ids = db.scalars(
        select(TicketType.match_id).where(TicketType.is_active.is_(True)).distinct()
    ).all()
    if not match_ids:
        return []
    matches = db.scalars(
        fixtures.match_query()
        .where(Match.id.in_(match_ids), Match.status == MatchStatus.SCHEDULED)
        .order_by(Match.kickoff_at)
    )
    out = []
    for m in matches:
        if m.kickoff_at and m.kickoff_at <= at:
            continue
        types = [_view(db, t, m, at) for t in _types(db, m.id, active_only=True)]
        out.append(ts.MatchTickets(match=fixtures.to_out(m), types=types))
    return out


def match_tickets(db: Session, match_id: uuid.UUID) -> ts.MatchTickets:
    at = now()
    m = _match(db, match_id)
    types = [_view(db, t, m, at) for t in _types(db, m.id, active_only=True)]
    return ts.MatchTickets(match=fixtures.to_out(m), types=types)


# --- Administration des catégories --------------------------------------------------------
def admin_types(db: Session, match_id: uuid.UUID) -> list[ts.TicketTypeAdminOut]:
    at = now()
    m = _match(db, match_id)
    return [_view(db, t, m, at, admin=True) for t in _types(db, m.id, active_only=False)]


def _check_window(opens_at, closes_at) -> None:
    if opens_at and closes_at and closes_at <= opens_at:
        raise BusinessError("La fin des ventes doit suivre leur ouverture")


def create_type(db: Session, actor, body: ts.TicketTypeIn) -> ts.TicketTypeAdminOut:
    m = _match(db, body.match_id)
    if m.status != MatchStatus.SCHEDULED:
        raise BusinessError("Ce match n'est plus à venir")
    _check_window(body.sales_open_at, body.sales_close_at)
    tt = TicketType(season_id=m.season_id, **body.model_dump())
    db.add(tt)
    db.flush()
    audit.record(db, actor, "create", "ticket_type", tt.id, body.model_dump(mode="json"))
    return _view(db, tt, m, now(), admin=True)


def update_type(db: Session, actor, tt_id: uuid.UUID, body: ts.TicketTypeUpdate):
    tt = db.get(TicketType, tt_id)
    if tt is None:
        raise NotFound("Catégorie introuvable")
    changes = body.model_dump(exclude_unset=True)
    if "price_fcfa" in changes and changes["price_fcfa"] != tt.price_fcfa:
        sold, reserved = _counts(db, tt.id, now())
        if sold or reserved:
            raise BusinessError("Le prix ne peut plus changer : des billets sont déjà vendus")
    if "quota" in changes and changes["quota"] is not None:
        sold, reserved = _counts(db, tt.id, now())
        if changes["quota"] < sold + reserved:
            raise BusinessError(
                f"Quota inférieur aux places déjà vendues ou réservées ({sold + reserved})"
            )
    _check_window(
        changes.get("sales_open_at", tt.sales_open_at),
        changes.get("sales_close_at", tt.sales_close_at),
    )
    before = {k: getattr(tt, k) for k in changes}
    for k, v in changes.items():
        setattr(tt, k, v)
    audit.record(
        db,
        actor,
        "update",
        "ticket_type",
        tt.id,
        {k: [str(before[k]), str(v)] for k, v in changes.items()},
    )
    return _view(db, tt, _match(db, tt.match_id), now(), admin=True)


# --- Commande et paiement -----------------------------------------------------------------
def create_order(db: Session, body: ts.OrderIn, ip: str | None) -> ts.OrderCreated:
    s = get_settings()
    at = now()
    # Verrou sur la catégorie : deux commandes simultanées ne peuvent pas dépasser le quota
    tt = db.scalar(select(TicketType).where(TicketType.id == body.ticket_type_id).with_for_update())
    if tt is None:
        raise NotFound("Catégorie introuvable")
    m = _match(db, tt.match_id)
    view = _view(db, tt, m, at)
    if view.state != rules.ON_SALE:
        msg = {
            rules.NOT_OPEN: "Les ventes ne sont pas encore ouvertes",
            rules.SOLD_OUT: "Complet : il n'y a plus de places dans cette catégorie",
        }.get(view.state, "Les ventes sont closes pour ce match")
        raise BusinessError(msg, code="not_on_sale")
    try:
        rules.check_quantity(body.quantity, max_per_order=tt.max_per_order, left=view.remaining)
    except rules.OrderError as exc:
        raise BusinessError(str(exc), code="quantity") from exc

    phone = normalize_phone(body.phone)
    allowed = [c.strip() for c in s.ticket_allowed_country_codes.split(",") if c.strip()]
    if not phone_allowed(phone, allowed):
        raise BusinessError(
            "Numéro non accepté (numéros du Burkina Faso uniquement)", code="phone_not_allowed"
        )
    pidx = phone_index(phone)
    ratelimit.hit(
        f"order:phone:{pidx}", limit=ORDERS_PER_PHONE[0], window_seconds=ORDERS_PER_PHONE[1]
    )
    if ip:
        ip_key = hmac.new(b"lds-order-ip", ip.encode(), hashlib.sha256).hexdigest()[:32]
        ratelimit.hit(f"order:ip:{ip_key}", limit=ORDERS_PER_IP[0], window_seconds=ORDERS_PER_IP[1])

    try:
        provider = get_payment_provider()
    except PaymentDisabled as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Le paiement en ligne n'est pas encore disponible",
        ) from exc

    reference = rules.random_code("CMD")
    key = _access_key(reference)
    order = Order(
        reference=reference,
        kind=OrderKind.TICKETS,
        status=OrderStatus.PENDING,
        amount_fcfa=tt.price_fcfa * body.quantity,
        phone=phone,
        phone_index=pidx,
        provider=provider.name,
        ticket_type_id=tt.id,
        quantity=body.quantity,
        buyer_name=body.buyer_name.strip(),
        expires_at=at + rules.RESERVATION_TTL,
        access_key_hash=_key_hash(key),
    )
    db.add(order)
    db.flush()
    return_url = f"{s.public_base_url}/billets/{order.reference}?k={key}"
    try:
        session = provider.create(
            reference=order.reference,
            amount_fcfa=order.amount_fcfa,
            phone=phone,
            callback_url=f"{s.payment_callback_base_url or s.api_base_url}/api/v1/payments/notify",
            return_url=return_url,
        )
    except Exception as exc:  # noqa: BLE001 — l'agrégateur peut échouer de mille façons
        log.warning("Création du paiement impossible : %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Paiement indisponible, réessayez plus tard"
        ) from exc
    order.provider_reference = session.provider_reference
    audit.record(
        db,
        None,
        "create",
        "order",
        order.id,
        {
            "reference": order.reference,
            "ticket_type_id": tt.id,
            "quantity": body.quantity,
            "amount_fcfa": order.amount_fcfa,
        },
    )
    return ts.OrderCreated(
        reference=order.reference,
        access_key=key,
        checkout_url=session.checkout_url,
        expires_at=order.expires_at,
        amount_fcfa=order.amount_fcfa,
    )


def _ticket_payload(t: Ticket, tt: TicketType, m: Match, season: Season) -> dict:
    """Le strict nécessaire au contrôle : ni nom ni numéro de l'acheteur."""
    payload = {
        "kid": get_settings().licence_key_id,
        "c": t.code,
        "m": str(m.id),
        "t": tt.name,
        "s": season.year,
    }
    if m.home_team and m.away_team:
        payload["mt"] = f"{m.home_team.short_name} – {m.away_team.short_name}"
    if m.kickoff_at:
        payload["d"] = m.kickoff_at.isoformat()
    return payload


def _issue(db: Session, order: Order, tt: TicketType) -> list[Ticket]:
    m = _match(db, tt.match_id)
    season = db.get(Season, tt.season_id)
    key = licences._signing_key()
    issued = []
    for _ in range(order.quantity or 0):
        t = Ticket(
            id=uuid.uuid4(),
            order_id=order.id,
            ticket_type_id=tt.id,
            match_id=m.id,
            code=rules.random_code("B"),
            holder_name=order.buyer_name,
            status=TicketStatus.VALID,
        )
        t.token = signed_token.sign(
            _ticket_payload(t, tt, m, season), key, prefix=signed_token.TICKET_PREFIX
        )
        db.add(t)
        issued.append(t)
    db.flush()
    return issued


def _raw_callback(body: bytes) -> dict:
    try:
        data = json.loads(body)
    except ValueError:
        data = None
    return data if isinstance(data, dict) else {"raw": body.decode("utf-8", "replace")[:4000]}


def handle_notification(db: Session, body: bytes, headers: Mapping[str, str]) -> None:
    """Notification de l'agrégateur (idempotente : un agrégateur peut renvoyer plusieurs fois).

    La signature est vérifiée sur le corps brut avant toute lecture de la commande.
    """
    try:
        note = get_payment_provider().parse_notification(body, headers)
    except PaymentDisabled as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Paiement désactivé") from exc
    except InvalidSignature as exc:
        log.warning("Notification de paiement à la signature invalide refusée")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Signature invalide") from exc
    except (KeyError, ValueError) as exc:
        raise BusinessError("Notification illisible") from exc
    order = db.scalar(select(Order).where(Order.reference == note.reference).with_for_update())
    if order is None or order.provider_reference != note.provider_reference:
        raise NotFound("Commande inconnue")
    if order.status != OrderStatus.PENDING:
        return  # déjà traitée
    order.raw_callback = _raw_callback(body)
    if not note.succeeded:
        order.status = OrderStatus.FAILED
        audit.record(db, None, "payment_failed", "order", order.id, {"reference": order.reference})
        return
    if note.amount != order.amount_fcfa:
        audit.record(
            db,
            None,
            "payment_mismatch",
            "order",
            order.id,
            {"expected": order.amount_fcfa, "received": note.amount},
        )
        return  # reste en attente : examen manuel

    tt = db.scalar(
        select(TicketType).where(TicketType.id == order.ticket_type_id).with_for_update()
    )
    order.paid_at = now()
    sold, reserved = _counts(db, tt.id, order.paid_at, exclude_order=order.id)
    late = order.expires_at and order.expires_at < order.paid_at
    if late and tt.quota is not None and sold + reserved + order.quantity > tt.quota:
        # Paiement arrivé après la réservation et plus de place : à rembourser
        order.status = OrderStatus.CANCELLED
        audit.record(
            db,
            None,
            "refund_required",
            "order",
            order.id,
            {"reference": order.reference, "amount_fcfa": order.amount_fcfa},
        )
        return
    order.status = OrderStatus.PAID
    tickets = _issue(db, order, tt)
    audit.record(
        db,
        None,
        "paid",
        "order",
        order.id,
        {"reference": order.reference, "tickets": [t.code for t in tickets]},
    )
    _send_link(order)


def _send_link(order: Order) -> None:
    key = _access_key(order.reference)
    url = f"{get_settings().public_base_url}/billets/{order.reference}?k={key}"
    try:
        get_sms_provider().send(
            order.phone,
            f"LDS : vos {order.quantity} billet(s) sont prêts. "
            f"Présentez le QR code à l'entrée : {url}",
        )
    except Exception:  # noqa: BLE001 — le paiement est acquis, l'échec du SMS est journalisé
        log.exception("SMS de billets non envoyé pour %s", order.reference)


# --- Consultation des billets (lien secret) -----------------------------------------------
def _authorized(order: Order, key: str) -> bool:
    return bool(order.access_key_hash) and hmac.compare_digest(
        order.access_key_hash, _key_hash(key)
    )


def get_order(db: Session, reference: str, key: str) -> Order:
    order = db.scalar(select(Order).where(Order.reference == reference))
    if order is None or not _authorized(order, key):
        raise NotFound("Commande introuvable (lien incomplet ou erroné)")
    return order


def _state(order: Order, at: datetime) -> str:
    if order.status == OrderStatus.PENDING and order.expires_at and order.expires_at < at:
        return "expired"
    return order.status.value


def order_view(db: Session, order: Order) -> ts.OrderOut:
    tt = db.get(TicketType, order.ticket_type_id)
    m = _match(db, tt.match_id)
    tickets = db.scalars(select(Ticket).where(Ticket.order_id == order.id).order_by(Ticket.code))
    return ts.OrderOut(
        reference=order.reference,
        state=_state(order, now()),
        amount_fcfa=order.amount_fcfa,
        quantity=order.quantity or 0,
        buyer_name=order.buyer_name or "",
        phone_hint=mask_phone(order.phone) if order.phone else "",
        type_name=tt.name,
        match=fixtures.to_out(m),
        expires_at=order.expires_at,
        paid_at=order.paid_at,
        tickets=[
            ts.TicketOut(
                code=t.code,
                token=t.token,
                status=t.status,
                type_name=tt.name,
                scanned_at=t.scanned_at,
            )
            for t in tickets
        ],
    )


def ticket_token(db: Session, order: Order, code: str) -> str:
    t = db.scalar(select(Ticket).where(Ticket.order_id == order.id, Ticket.code == code))
    if t is None:
        raise NotFound("Billet introuvable")
    return t.token


# --- Suivi des ventes -----------------------------------------------------------------------
def admin_orders(
    db: Session, match_id: uuid.UUID, state: str | None = None
) -> list[ts.OrderAdminOut]:
    at = now()
    types = {t.id: t for t in _types(db, match_id, active_only=False)}
    if not types:
        return []
    orders = [
        o
        for o in db.scalars(
            select(Order)
            .where(Order.ticket_type_id.in_(types))
            .order_by(Order.created_at.desc())
            .limit(500)
        )
        if not state or _state(o, at) == state
    ]
    # Codes des billets en une seule requête (et non une par commande)
    codes: dict[uuid.UUID, list[str]] = {o.id: [] for o in orders}
    if orders:
        rows = db.execute(
            select(Ticket.order_id, Ticket.code)
            .where(Ticket.order_id.in_(list(codes)))
            .order_by(Ticket.code)
        )
        for order_id, code in rows:
            codes[order_id].append(code)
    out = []
    for o in orders:
        st = _state(o, at)
        out.append(
            ts.OrderAdminOut(
                reference=o.reference,
                state=st,
                amount_fcfa=o.amount_fcfa,
                quantity=o.quantity or 0,
                buyer_name=o.buyer_name or "",
                phone_hint=mask_phone(o.phone) if o.phone else "",
                type_name=types[o.ticket_type_id].name,
                created_at=o.created_at,
                paid_at=o.paid_at,
                provider=o.provider,
                tickets=codes[o.id],
            )
        )
    return out


def cancel_ticket(db: Session, actor, code: str, reason: str) -> None:
    t = db.scalar(select(Ticket).where(Ticket.code == code))
    if t is None:
        raise NotFound("Billet introuvable")
    if t.status == TicketStatus.CANCELLED:
        raise BusinessError("Billet déjà annulé")
    if t.status == TicketStatus.USED:
        raise BusinessError("Ce billet a déjà servi à entrer")
    t.status = TicketStatus.CANCELLED
    audit.record(db, actor, "cancel", "ticket", t.id, {"code": t.code, "reason": reason})


def current_matches(db: Session) -> list:
    """Matchs à venir de la saison en cours (pour créer des catégories de billets)."""
    season = seasons.current_season(db)
    return [
        fixtures.to_out(m)
        for m in db.scalars(
            fixtures.match_query()
            .where(Match.season_id == season.id, Match.status == MatchStatus.SCHEDULED)
            .order_by(Match.kickoff_at.nulls_last(), Match.round_number)
        )
    ]
