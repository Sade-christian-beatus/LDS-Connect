import uuid
from datetime import UTC, datetime, timedelta

import pytest

from lds_api.domain.voting import (
    CLOSED,
    DRAFT,
    OPEN,
    UPCOMING,
    ChoiceError,
    RecentVote,
    effective_state,
    fraud_reasons,
    phone_allowed,
    results_visible,
    validate_choices,
)

T0 = datetime(2027, 1, 10, 12, 0, tzinfo=UTC)
OPENS, CLOSES = T0, T0 + timedelta(days=2)


@pytest.mark.parametrize(
    ("status", "now", "expected"),
    [
        ("draft", T0 + timedelta(hours=1), DRAFT),
        ("open", T0 - timedelta(hours=1), UPCOMING),
        ("open", T0 + timedelta(hours=1), OPEN),
        ("open", CLOSES, CLOSED),
        ("closed", T0 + timedelta(hours=1), CLOSED),  # clôture anticipée
        ("published", T0 + timedelta(hours=1), CLOSED),
    ],
)
def test_effective_state(status, now, expected):
    assert effective_state(status, OPENS, CLOSES, now) == expected


def test_results_visibility():
    common = {"publish_at": None, "now": T0}
    assert results_visible(status="open", visibility="immediate", state=OPEN, **common)
    assert not results_visible(status="open", visibility="immediate", state=UPCOMING, **common)
    later = T0 + timedelta(days=5)
    assert not results_visible(
        status="closed", visibility="scheduled", publish_at=later, state=CLOSED, now=T0
    )
    assert results_visible(
        status="closed", visibility="scheduled", publish_at=later, state=CLOSED, now=later
    )
    assert results_visible(
        status="published", visibility="scheduled", publish_at=None, state=CLOSED, now=T0
    )


def test_validate_choices():
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    allowed = {a, b, c}
    assert validate_choices([a], allowed, 1) == [a]
    assert validate_choices([a, b], allowed, 11) == [a, b]
    for bad, message in (
        ([], "au moins"),
        ([a, a], "deux fois"),
        ([a, b], "1 choix"),
        ([uuid.uuid4()], "inconnue"),
    ):
        with pytest.raises(ChoiceError, match=message):
            validate_choices(bad, allowed, 1 if message == "1 choix" else 11)


@pytest.mark.parametrize(
    ("phone", "ok"),
    [
        ("+22670123456", True),
        ("+2267012345", False),
        ("+33612345678", False),
        ("+226701234567", False),
    ],
)
def test_phone_allowed_burkina_only(phone, ok):
    assert phone_allowed(phone, ["226"]) is ok


def test_fraud_same_connection():
    recent = [
        RecentVote(f"+226700000{i:02d}", "ip-1", T0 - timedelta(minutes=2)) for i in range(10)
    ]
    assert fraud_reasons(phone="+22671111111", ip_hash="ip-1", now=T0, recent=recent)
    assert fraud_reasons(phone="+22671111111", ip_hash="ip-2", now=T0, recent=recent[:3]) == []


def test_fraud_sequential_numbers():
    recent = [
        RecentVote(f"+22670000{100 + i}", f"ip-{i}", T0 - timedelta(minutes=1)) for i in range(5)
    ]
    reasons = fraud_reasons(phone="+22670000106", ip_hash="ip-x", now=T0, recent=recent)
    assert reasons == ["série de numéros qui se suivent"]
    # Votes anciens (hors fenêtre) ignorés
    old = [RecentVote(v.phone, v.ip_hash, T0 - timedelta(hours=2)) for v in recent]
    assert fraud_reasons(phone="+22670000106", ip_hash="ip-x", now=T0, recent=old) == []
