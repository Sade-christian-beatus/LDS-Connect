"""Billetterie : catégories, commande sans compte, paiement, billets QR, contrôle d'accès,
accréditations."""

import base64
import json
import uuid
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select

from lds_api.models import Match, Order
from lds_api.models.enums import MatchStatus
from lds_api.providers.payment import PaymentSession, SimulatorPaymentProvider, sign
from lds_api.providers.sms import SmsResult
from lds_api.services import ticketing


class FakeSms:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send(self, to, message):
        self.sent.append((to, message))
        return SmsResult(provider_id="fake", accepted=True)


class FakePayment:
    """Agrégateur factice : enregistre les paiements demandés, sans réseau."""

    name = "fake"

    def __init__(self):
        self.created: list[dict] = []
        self._secret = ""

    def create(self, *, reference, amount_fcfa, phone, callback_url, return_url=None):
        pid = f"pay-{len(self.created) + 1}"
        self.created.append(
            {"id": pid, "reference": reference, "amount": amount_fcfa, "return_url": return_url}
        )
        return PaymentSession(pid, f"https://paiement.test/{pid}")

    parse_notification = SimulatorPaymentProvider.parse_notification


@pytest.fixture
def sms(monkeypatch):
    fake = FakeSms()
    monkeypatch.setattr(ticketing, "get_sms_provider", lambda: fake)
    return fake


@pytest.fixture
def pay(monkeypatch):
    fake = FakePayment()
    monkeypatch.setattr(ticketing, "get_payment_provider", lambda: fake)
    return fake


@pytest.fixture
def match(db, seeded) -> Match:
    m = db.scalars(
        select(Match).where(Match.status == MatchStatus.SCHEDULED, Match.home_team_id.is_not(None))
    ).first()
    m.kickoff_at = datetime.now(UTC) + timedelta(days=3)
    db.flush()
    return m


@pytest.fixture
def other_match(db, match) -> Match:
    m = db.scalars(
        select(Match).where(
            Match.status == MatchStatus.SCHEDULED,
            Match.home_team_id.is_not(None),
            Match.id != match.id,
        )
    ).first()
    m.kickoff_at = datetime.now(UTC) + timedelta(days=4)
    db.flush()
    return m


def make_type(client, headers, match, **extra):
    body = {"match_id": str(match.id), "name": "Tribune", "price_fcfa": 2000, "quota": 5, **extra}
    r = client.post("/api/v1/admin/ticket-types", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def order(client, tt, quantity=2, phone="70 11 22 33"):
    return client.post(
        "/api/v1/tickets/orders",
        json={
            "ticket_type_id": tt["id"],
            "quantity": quantity,
            "buyer_name": "Awa Ouédraogo",
            "phone": phone,
        },
    )


def notify(client, pay, created, status="succeeded", amount=None, signature=None):
    p = next(x for x in pay.created if x["reference"] == created["reference"])
    body = json.dumps(
        {
            "id": p["id"],
            "reference": p["reference"],
            "status": status,
            "amount": p["amount"] if amount is None else amount,
        }
    ).encode()
    headers = {"content-type": "application/json"}
    if signature is None and pay._secret:
        signature = sign(pay._secret, body)
    if signature:
        headers["x-lds-signature"] = signature
    return client.post("/api/v1/payments/notify", content=body, headers=headers)


def view(client, created):
    return client.get(
        f"/api/v1/tickets/orders/{created['reference']}", params={"k": created["access_key"]}
    )


def buy(client, pay, tt, quantity=2, phone="70 11 22 33") -> dict:
    r = order(client, tt, quantity, phone)
    assert r.status_code == 201, r.text
    created = r.json()
    assert notify(client, pay, created).status_code == 204
    return view(client, created).json()


def scan(client, headers, token, match=None, at=None, device="Porte A", client_id=None):
    body = {
        "scans": [
            {
                "client_id": str(client_id or uuid.uuid4()),
                "token": token,
                "match_id": str(match.id) if match else None,
                "scanned_at": (at or datetime.now(UTC)).isoformat(),
                "device": device,
            }
        ]
    }
    r = client.post("/api/v1/access/scans", json=body, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()[0]


# --- Catégories et ventes --------------------------------------------------------------------
def test_permissions(client, as_admin, as_club, as_controller, match):
    body = {"match_id": str(match.id), "name": "Tribune", "price_fcfa": 1000}
    assert client.post("/api/v1/admin/ticket-types", json=body, headers=as_club).status_code == 403
    r = client.post("/api/v1/admin/ticket-types", json=body, headers=as_controller)
    assert r.status_code == 403
    assert client.get("/api/v1/access/matches", headers=as_club).status_code == 403
    assert client.get("/api/v1/access/matches", headers=as_controller).status_code == 200
    assert client.get("/api/v1/admin/accreditations", headers=as_controller).status_code == 403


def test_public_listing_and_reservation(client, as_admin, pay, sms, match):
    tt = make_type(client, as_admin, match)
    listing = client.get("/api/v1/tickets/matches").json()
    entry = next(x for x in listing if x["match"]["id"] == str(match.id))
    assert entry["types"][0]["remaining"] == 5 and entry["types"][0]["state"] == "on_sale"

    r = order(client, tt, quantity=3)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["amount_fcfa"] == 6000
    assert created["checkout_url"].startswith("https://paiement.test/")
    # Le retour après paiement mène à la page des billets, avec la clé
    ret = urlparse(pay.created[0]["return_url"])
    assert ret.path == f"/billets/{created['reference']}"
    assert parse_qs(ret.query)["k"] == [created["access_key"]]

    # Places réservées pendant le paiement : il n'en reste que 2
    t = client.get(f"/api/v1/tickets/matches/{match.id}").json()["types"][0]
    assert t["remaining"] == 2
    assert order(client, tt, quantity=3, phone="70 11 22 44").json()["detail"] == (
        "Plus assez de places disponibles"
    )
    # Commande en attente visible par la clé seulement
    assert view(client, created).json()["state"] == "pending"
    bad = client.get(f"/api/v1/tickets/orders/{created['reference']}", params={"k": "x" * 24})
    assert bad.status_code == 404


def test_validation(client, as_admin, pay, match):
    tt = make_type(client, as_admin, match, max_per_order=4)
    assert order(client, tt, quantity=5).json()["detail"] == "4 billets au maximum par commande"
    r = order(client, tt, phone="+33 6 12 34 56 78")
    assert r.status_code == 422 and "Burkina" in r.json()["detail"]
    later = make_type(
        client,
        as_admin,
        match,
        name="Prévente",
        sales_open_at=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
    )
    assert order(client, later).json()["detail"] == "Les ventes ne sont pas encore ouvertes"


def test_payment_issues_signed_tickets_and_sms(client, db, as_admin, pay, sms, match):
    tt = make_type(client, as_admin, match)
    o = buy(client, pay, tt, quantity=2)
    assert o["state"] == "paid" and len(o["tickets"]) == 2
    assert o["phone_hint"].endswith("22 33") and "7011" not in o["phone_hint"]
    tok = o["tickets"][0]["token"]
    assert tok.startswith("LDT1.")
    # Le QR ne contient ni nom ni numéro de l'acheteur
    body = tok.split(".")[1]
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    assert payload["m"] == str(match.id) and payload["t"] == "Tribune"
    assert "Awa" not in json.dumps(payload) and "7011" not in json.dumps(payload)

    # SMS avec le lien des billets (même clé que celle donnée au navigateur)
    to, msg = sms.sent[-1]
    assert to == "+22670112233" and f"/billets/{o['reference']}?k=" in msg
    key = msg.rsplit("k=", 1)[1]
    assert (
        client.get(f"/api/v1/tickets/orders/{o['reference']}", params={"k": key}).status_code == 200
    )

    svg = client.get(
        f"/api/v1/tickets/orders/{o['reference']}/tickets/{o['tickets'][0]['code']}.svg",
        params={"k": key},
    )
    assert svg.status_code == 200 and svg.text.startswith("<svg")

    # Notification répétée : pas de billets en double
    order_row = db.scalar(select(Order).where(Order.reference == o["reference"]))
    created = {"reference": o["reference"], "access_key": key}
    assert notify(client, pay, created).status_code == 204
    assert len(view(client, created).json()["tickets"]) == 2
    assert order_row.status.value == "paid"

    admin = client.get(f"/api/v1/admin/ticket-types?match_id={match.id}", headers=as_admin).json()
    assert admin[0]["sold"] == 2 and admin[0]["revenue_fcfa"] == 4000
    orders = client.get(f"/api/v1/admin/orders?match_id={match.id}", headers=as_admin).json()
    assert orders[0]["buyer_name"] == "Awa Ouédraogo" and len(orders[0]["tickets"]) == 2
    # Prix figé une fois des billets vendus
    r = client.patch(
        f"/api/v1/admin/ticket-types/{tt['id']}", json={"price_fcfa": 3000}, headers=as_admin
    )
    assert r.status_code == 422


def test_failed_and_mismatched_payments(client, as_admin, pay, sms, match):
    tt = make_type(client, as_admin, match)
    failed = order(client, tt, quantity=5).json()
    assert notify(client, pay, failed, status="failed").status_code == 204
    assert view(client, failed).json()["state"] == "failed"
    # Les places sont libérées
    assert client.get(f"/api/v1/tickets/matches/{match.id}").json()["types"][0]["remaining"] == 5

    odd = order(client, tt, quantity=1).json()
    assert notify(client, pay, odd, amount=1).status_code == 204
    o = view(client, odd).json()
    assert o["state"] == "pending" and o["tickets"] == []


def test_notifications_must_be_signed(client, as_admin, pay, sms, match):
    pay._secret = "secret-de-test-partage-avec-l-agregateur"
    tt = make_type(client, as_admin, match)
    created = order(client, tt, quantity=1).json()
    # Sans signature, avec une signature fausse ou faite avec un autre secret : refusée
    for bad in ("", "sha256=" + "0" * 64, sign("autre-secret", b"{}")):
        r = notify(client, pay, created, signature=bad or "absente")
        assert r.status_code == 401, r.text
    assert view(client, created).json()["state"] == "pending"
    # Un montant modifié après signature ne passe pas non plus
    p = pay.created[-1]
    body = json.dumps({**p, "status": "succeeded"}).encode()
    forged = body.replace(str(p["amount"]).encode(), b"1")
    r = client.post(
        "/api/v1/payments/notify",
        content=forged,
        headers={"x-lds-signature": sign(pay._secret, body)},
    )
    assert r.status_code == 401
    # Signée par l'agrégateur : acceptée
    assert notify(client, pay, created).status_code == 204
    assert view(client, created).json()["state"] == "paid"


def test_late_payment_without_seats_is_cancelled(client, db, as_admin, pay, sms, match):
    tt = make_type(client, as_admin, match, quota=2)
    first = order(client, tt, quantity=2).json()
    # La réservation expire, quelqu'un d'autre achète les places
    row = db.scalar(select(Order).where(Order.reference == first["reference"]))
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.flush()
    buy(client, pay, tt, quantity=2, phone="70 99 88 77")
    assert notify(client, pay, first).status_code == 204
    assert view(client, first).json()["state"] == "cancelled"  # à rembourser (journal d'audit)


# --- Contrôle d'accès ------------------------------------------------------------------------
def test_scans_admit_once_and_detect_duplicates(
    client, as_admin, as_controller, pay, sms, match, other_match
):
    tt = make_type(client, as_admin, match)
    o = buy(client, pay, tt, quantity=2)
    t1, t2 = (t["token"] for t in o["tickets"])

    manifest = client.get(
        f"/api/v1/access/matches/{match.id}/manifest", headers=as_controller
    ).json()
    assert {x["c"] for x in manifest["tickets"]} == {t["code"] for t in o["tickets"]}

    cid = uuid.uuid4()
    first = scan(client, as_controller, t1, match, client_id=cid)
    assert first["result"] == "admitted" and first["label"] == "Tribune"
    # Renvoi du même passage (synchronisation répétée) : même réponse, pas de doublon
    assert scan(client, as_controller, t1, match, client_id=cid)["result"] == "admitted"
    dup = scan(client, as_controller, t1, match, device="Porte B")
    assert dup["result"] == "duplicate" and "Porte A" in dup["detail"]

    assert scan(client, as_controller, t2, other_match)["result"] == "wrong_match"
    forged = t2[:-4] + ("AAAA" if not t2.endswith("AAAA") else "BBBB")
    assert scan(client, as_controller, forged, match)["result"] == "invalid"
    assert scan(client, as_controller, "n'importe quoi", match)["kind"] == "unknown"

    stats = client.get(f"/api/v1/access/matches/{match.id}/stats", headers=as_controller).json()
    assert stats["tickets_sold"] == 2 and stats["admitted"] == 1 and stats["duplicates"] == 1


def test_offline_scans_from_two_devices(client, as_admin, as_controller, pay, sms, match):
    tt = make_type(client, as_admin, match)
    token = buy(client, pay, tt, quantity=1)["tickets"][0]["token"]
    t0 = datetime.now(UTC)
    # La porte B synchronise d'abord un passage de 18 h 05…
    assert (
        scan(client, as_controller, token, match, at=t0 + timedelta(minutes=5), device="Porte B")[
            "result"
        ]
        == "admitted"
    )
    # … puis la porte A, restée hors ligne, envoie son passage de 18 h 00 : c'est l'entrée
    assert (
        scan(client, as_controller, token, match, at=t0, device="Porte A")["result"] == "admitted"
    )
    stats = client.get(f"/api/v1/access/matches/{match.id}/stats", headers=as_controller).json()
    assert stats["admitted"] == 1 and stats["duplicates"] == 1


def test_cancelled_ticket_is_refused(client, as_admin, as_controller, pay, sms, match):
    tt = make_type(client, as_admin, match)
    t = buy(client, pay, tt, quantity=1)["tickets"][0]
    r = client.post(
        f"/api/v1/admin/tickets/{t['code']}/cancel", json={"reason": "Doublon"}, headers=as_admin
    )
    assert r.status_code == 204
    res = scan(client, as_controller, t["token"], match)
    assert res["result"] == "invalid" and res["detail"] == "Billet annulé"


# --- Accréditations --------------------------------------------------------------------------
def test_accreditation_lifecycle(client, as_admin, as_controller, match):
    today = date.today()
    r = client.post(
        "/api/v1/admin/accreditations",
        json={
            "full_name": "Mariam Kaboré",
            "organisation": "Sidwaya",
            "category": "press",
            "zones": ["Tribune de presse", "Zone mixte"],
            "valid_from": str(today),
            "valid_until": str(today + timedelta(days=30)),
        },
        headers=as_admin,
    )
    assert r.status_code == 201, r.text
    acc = r.json()
    assert acc["token"].startswith("LDA1.") and acc["code"].startswith("A-")
    qr = client.get(f"/api/v1/admin/accreditations/{acc['id']}/qr.svg", headers=as_admin)
    assert qr.status_code == 200

    # Plusieurs entrées possibles
    for _ in range(2):
        res = scan(client, as_controller, acc["token"], match)
        assert res["result"] == "admitted" and res["label"] == "Mariam Kaboré"

    r = client.post(
        f"/api/v1/admin/accreditations/{acc['id']}/revoke",
        json={"reason": "Carte perdue"},
        headers=as_admin,
    )
    assert r.status_code == 200 and r.json()["revoked_at"]
    res = scan(client, as_controller, acc["token"], match)
    assert res["result"] == "invalid" and "révoquée" in res["detail"]
    manifest = client.get(
        f"/api/v1/access/matches/{match.id}/manifest", headers=as_controller
    ).json()
    assert acc["code"] in manifest["revoked_accreditations"]


def test_payment_disabled_is_explicit(client, as_admin, match, monkeypatch):
    monkeypatch.setenv("PAYMENT_PROVIDER", "disabled")
    from lds_api.core.config import get_settings

    get_settings.cache_clear()
    try:
        tt = make_type(client, as_admin, match)
        r = order(client, tt)
        assert r.status_code == 503 and "pas encore disponible" in r.json()["detail"]
    finally:
        get_settings.cache_clear()
