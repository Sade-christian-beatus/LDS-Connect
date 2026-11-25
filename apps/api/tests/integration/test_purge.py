"""Purge des données à durée limitée (M5)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from lds_api.core.config import get_settings
from lds_api.models import AuditLog, Ballot, Order, Vote
from lds_api.models.enums import OrderKind, OrderStatus
from lds_api.models.voting import OtpChallenge
from lds_api.services.purge import purge


def _order(db, ref, status, created, paid_at=None):
    o = Order(
        reference=ref,
        kind=OrderKind.TICKETS,
        status=status,
        amount_fcfa=1000,
        phone="+22670000000",
        phone_index=f"idx-{ref}",
        provider="simulator",
        buyer_name="Awa O.",
        paid_at=paid_at,
        created_at=created,
    )
    db.add(o)
    return o


def test_purge_respects_retention(db, seeded, monkeypatch):
    now = datetime.now(UTC)
    old, recent = now - timedelta(days=45), now - timedelta(days=2)
    old_unpaid = _order(db, "CMD-OLD-1", OrderStatus.FAILED, old)
    new_unpaid = _order(db, "CMD-NEW-1", OrderStatus.PENDING, recent)
    paid = _order(db, "CMD-PAID-1", OrderStatus.PAID, old, paid_at=old)

    ballot = db.scalar(select(Ballot).limit(1))
    challenge = None
    if ballot is not None:
        ballot.closes_at = old
        challenge = OtpChallenge(
            phone_index="p",
            phone="+22670000001",
            purpose="vote",
            ballot_id=ballot.id,
            code_hash="x",
            created_at=old,
            expires_at=old,
        )
        db.add(challenge)
    db.commit()

    report = purge(db, dry_run=True)
    assert report.unpaid_orders >= 1
    db.refresh(old_unpaid)
    assert old_unpaid.phone_index is not None  # simulation : rien d'effacé

    report = purge(db)
    db.commit()
    db.expire_all()
    assert db.get(Order, old_unpaid.id).phone is None
    assert db.get(Order, old_unpaid.id).buyer_name is None
    assert db.get(Order, new_unpaid.id).phone_index is not None  # trop récente
    assert db.get(Order, paid.id).phone_index is not None  # durée non fixée : conservée
    if challenge is not None:
        assert db.get(OtpChallenge, challenge.id) is None
        assert not db.scalars(select(Vote).where(Vote.otp_challenge_id == challenge.id)).all()
    log = db.scalars(select(AuditLog).where(AuditLog.action == "purge")).all()[-1]
    assert log.changes["unpaid_orders"] == report.unpaid_orders

    # Durée fixée pour les commandes payées : le numéro disparaît, le nom reste
    monkeypatch.setattr(get_settings(), "retention_paid_order_phone_days", 30)
    purge(db)
    db.commit()
    db.expire_all()
    p = db.get(Order, paid.id)
    assert p.phone_index is None and p.buyer_name == "Awa O."
