"""Règles de billetterie et de contrôle d'accès (fonctions pures)."""

import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from lds_api.domain import ticketing as t

NOW = datetime(2027, 3, 10, 12, tzinfo=UTC)
KICKOFF = NOW + timedelta(days=2)


def state(**kw):
    base = {
        "is_active": True,
        "opens_at": None,
        "closes_at": None,
        "kickoff_at": KICKOFF,
        "left": 100,
        "now": NOW,
    }
    return t.sale_state(**{**base, **kw})


def test_sale_state():
    assert state() == t.ON_SALE
    assert state(is_active=False) == t.CLOSED
    assert state(opens_at=NOW + timedelta(hours=1)) == t.NOT_OPEN
    assert state(closes_at=NOW - timedelta(minutes=1)) == t.CLOSED
    assert state(kickoff_at=NOW) == t.CLOSED  # ventes closes au coup d'envoi par défaut
    assert (
        state(closes_at=NOW + timedelta(hours=1), kickoff_at=NOW - timedelta(hours=1)) == t.ON_SALE
    )
    assert state(left=0) == t.SOLD_OUT
    assert state(left=None) == t.ON_SALE  # sans quota


def test_remaining():
    assert t.remaining(None, 50) is None
    assert t.remaining(100, 30) == 70
    assert t.remaining(10, 12) == 0


def test_check_quantity():
    t.check_quantity(3, max_per_order=10, left=3)
    t.check_quantity(3, max_per_order=10, left=None)
    with pytest.raises(t.OrderError, match="maximum"):
        t.check_quantity(11, max_per_order=10, left=None)
    with pytest.raises(t.OrderError, match="Plus assez"):
        t.check_quantity(4, max_per_order=10, left=3)
    with pytest.raises(t.OrderError, match="Complet"):
        t.check_quantity(1, max_per_order=10, left=0)


def test_codes_are_unambiguous():
    codes = {t.random_code("B") for _ in range(500)}
    assert len(codes) == 500
    for c in codes:
        assert re.fullmatch(r"B-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{8}", c)


M1, M2 = uuid.uuid4(), uuid.uuid4()


def decide(**kw):
    base = {
        "ticket_status": "valid",
        "ticket_match_id": M1,
        "scan_match_id": M1,
        "first_entry": None,
        "scanned_at": NOW,
    }
    return t.decide_ticket(**{**base, **kw})


def test_ticket_decisions():
    assert decide().result == "admitted"
    assert decide(ticket_status="cancelled").result == "invalid"
    assert decide(scan_match_id=M2).result == "wrong_match"
    assert decide(scan_match_id=None).result == "admitted"  # contrôle sans match choisi
    prior = t.PriorEntry(NOW - timedelta(minutes=5), "Porte A")
    d = decide(first_entry=prior)
    assert d.result == "duplicate" and "Porte A" in d.detail and "11:55" in d.detail


def test_offline_scan_earlier_than_known_entry_wins():
    """Deux appareils hors ligne : le passage le plus ancien reste l'entrée."""
    later = t.PriorEntry(NOW + timedelta(minutes=3), "Porte B")
    assert decide(first_entry=later).result == "admitted"
