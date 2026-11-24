import json

import httpx
import pytest

from lds_api.providers.payment import InvalidSignature, SimulatorPaymentProvider, sign
from lds_api.providers.sms import ConsoleSmsProvider, SimulatorSmsProvider
from lds_api.providers.storage import LocalStorage


def mock_client(handler) -> httpx.Client:
    return httpx.Client(base_url="http://simulateurs", transport=httpx.MockTransport(handler))


def test_sms_simulator_sends_payload():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content), path=request.url.path)
        return httpx.Response(200, json={"id": "abc", "status": "delivered"})

    result = SimulatorSmsProvider("http://simulateurs", mock_client(handler)).send(
        "+22600112233", "Code : 1234"
    )
    assert result.accepted and result.provider_id == "abc"
    assert seen == {
        "to": "+22600112233",
        "message": "Code : 1234",
        "sender": "LDS",
        "path": "/sms/send",
    }


def test_console_sms_masks_number(caplog):
    caplog.set_level("INFO")
    ConsoleSmsProvider().send("+22600112233", "Bonjour")
    assert "+2260011****" in caplog.text and "+22600112233" not in caplog.text


def test_payment_simulator_roundtrip():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["amount"] == 1000 and body["currency"] == "XOF"
        return httpx.Response(
            200, json={"id": "p1", "status": "pending", "checkout_url": "/payment/p1"}
        )

    provider = SimulatorPaymentProvider("http://simulateurs", mock_client(handler))
    session = provider.create(
        reference="CMD-1", amount_fcfa=1000, phone=None, callback_url="http://api/cb"
    )
    assert session.checkout_url == "http://simulateurs/payment/p1"
    body = json.dumps(
        {"id": "p1", "reference": "CMD-1", "status": "succeeded", "amount": 1000}
    ).encode()
    notif = provider.parse_notification(body, {})
    assert notif.succeeded and notif.reference == "CMD-1"


def test_payment_notification_signature():
    provider = SimulatorPaymentProvider("http://simulateurs", webhook_secret="s3cret")
    body = b'{"id": "p1", "reference": "CMD-1", "status": "succeeded", "amount": 1000}'
    assert provider.parse_notification(body, {"x-lds-signature": sign("s3cret", body)}).succeeded
    for headers in ({}, {"x-lds-signature": "sha256=abc"}, {"x-lds-signature": sign("x", body)}):
        with pytest.raises(InvalidSignature):
            provider.parse_notification(body, headers)


def test_local_storage_roundtrip_and_path_traversal(tmp_path):
    store = LocalStorage(str(tmp_path))
    store.put("photos/joueur.jpg", b"img", "image/jpeg")
    assert store.get("photos/joueur.jpg") == b"img"
    store.delete("photos/joueur.jpg")
    assert not (tmp_path / "photos" / "joueur.jpg").exists()
    for bad in ("../secret", "/etc/passwd", "a/../../b"):
        with pytest.raises(ValueError):
            store.put(bad, b"x", "text/plain")
