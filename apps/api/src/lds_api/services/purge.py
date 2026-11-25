"""Purge des données à durée de conservation limitée (audit M5).

Durées réglées par la Ligue (variables RETENTION_*, 0 = conserver sans limite) :
- codes de vote par SMS : le numéro chiffré est supprimé N jours après la clôture du scrutin ;
  les votes gardent seulement l'empreinte du numéro (un vote par personne reste contrôlable) ;
- commandes non payées (expirées, refusées, annulées) : nom et numéro effacés après N jours,
  la ligne reste pour la traçabilité comptable ;
- commandes payées : numéro de l'acheteur effacé N jours après le paiement (le nom reste sur
  les billets).
Chaque passage est inscrit au journal d'audit avec les nombres traités.
"""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.orm import Session

from lds_api.core.config import get_settings
from lds_api.models import Ballot, Order, Vote
from lds_api.models.enums import OrderStatus
from lds_api.models.voting import OtpChallenge
from lds_api.services import audit


@dataclass
class PurgeReport:
    otp_challenges: int = 0
    unpaid_orders: int = 0
    paid_order_phones: int = 0


def purge(db: Session, *, now: datetime | None = None, dry_run: bool = False) -> PurgeReport:
    s = get_settings()
    now = now or datetime.now(UTC)
    report = PurgeReport()

    if s.retention_otp_days > 0:
        limit = now - timedelta(days=s.retention_otp_days)
        closed = select(Ballot.id).where(Ballot.closes_at < limit)
        old = select(OtpChallenge.id).where(
            or_(
                OtpChallenge.ballot_id.in_(closed),
                and_(OtpChallenge.ballot_id.is_(None), OtpChallenge.created_at < limit),
            )
        )
        ids = list(db.scalars(old))
        report.otp_challenges = len(ids)
        if ids and not dry_run:
            db.execute(
                update(Vote).where(Vote.otp_challenge_id.in_(ids)).values(otp_challenge_id=None)
            )
            db.execute(delete(OtpChallenge).where(OtpChallenge.id.in_(ids)))

    if s.retention_unpaid_orders_days > 0:
        limit = now - timedelta(days=s.retention_unpaid_orders_days)
        unpaid = (
            Order.status.in_([OrderStatus.PENDING, OrderStatus.FAILED, OrderStatus.CANCELLED]),
            Order.paid_at.is_(None),
            Order.created_at < limit,
            or_(Order.phone_index.is_not(None), Order.buyer_name.is_not(None)),
        )
        ids = list(db.scalars(select(Order.id).where(*unpaid)))
        report.unpaid_orders = len(ids)
        if ids and not dry_run:
            db.execute(
                update(Order)
                .where(Order.id.in_(ids))
                .values(phone=None, phone_index=None, buyer_name=None, raw_callback=None)
            )

    if s.retention_paid_order_phone_days > 0:
        limit = now - timedelta(days=s.retention_paid_order_phone_days)
        paid = (Order.paid_at.is_not(None), Order.paid_at < limit, Order.phone_index.is_not(None))
        ids = list(db.scalars(select(Order.id).where(*paid)))
        report.paid_order_phones = len(ids)
        if ids and not dry_run:
            db.execute(update(Order).where(Order.id.in_(ids)).values(phone=None, phone_index=None))

    if not dry_run and any(asdict(report).values()):
        audit.record(db, None, "purge", "retention", None, asdict(report))
    return report
