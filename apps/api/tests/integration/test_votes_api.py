"""Votes du public : scrutins, code SMS, unicité, anti-fraude, résultats, procès-verbal."""

import hashlib
import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from lds_api.models import Team
from lds_api.providers.sms import SmsResult
from lds_api.services import voting

from .conftest import login


class FakeSms:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send(self, to: str, message: str) -> SmsResult:
        self.sent.append((to, message))
        return SmsResult(provider_id="fake", accepted=True)

    def last_code(self) -> str:
        return re.search(r"(\d{6})", self.sent[-1][1]).group(1)


@pytest.fixture
def sms(monkeypatch) -> FakeSms:
    fake = FakeSms()
    monkeypatch.setattr(voting, "get_sms_provider", lambda: fake)
    return fake


def iso(delta: timedelta) -> str:
    return (datetime.now(UTC) + delta).isoformat()


def make_ballot(client, headers, db, *, max_choices=1, open_now=True, **extra) -> dict:
    team = db.scalar(select(Team).where(Team.short_name == "Vinnim"))
    cands = client.get(
        "/api/v1/admin/ballots/candidates",
        params={"kind": "players", "team_id": str(team.id)},
        headers=headers,
    ).json()
    body = {
        "kind": "player_of_the_season",
        "title": "Joueur du mois (test)",
        "opens_at": iso(timedelta(hours=-1) if open_now else timedelta(days=1)),
        "closes_at": iso(timedelta(days=2)),
        "max_choices": max_choices,
        "options": [
            {"label": c["label"], "person_id": c["person_id"], "team_id": c["team_id"]}
            for c in cands[:5]
        ],
        **extra,
    }
    r = client.post("/api/v1/admin/ballots", json=body, headers=headers)
    assert r.status_code == 201, r.text
    ballot = r.json()
    assert ballot["state"] == "draft"
    r = client.post(f"/api/v1/admin/ballots/{ballot['id']}/open", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def vote(client, sms, ballot, phone, choices):
    r = client.post(
        f"/api/v1/ballots/{ballot['id']}/code", json={"phone": phone, "choices": choices}
    )
    assert r.status_code == 200, r.text
    challenge = r.json()["challenge_id"]
    return client.post(
        f"/api/v1/ballots/{ballot['id']}/vote",
        json={"challenge_id": challenge, "code": sms.last_code()},
    )


def test_admin_only_and_draft_hidden(client, db, as_admin, as_club, seeded):
    assert client.get("/api/v1/admin/ballots", headers=as_club).status_code == 403
    r = client.post(
        "/api/v1/admin/ballots",
        json={
            "kind": "special",
            "title": "Brouillon",
            "opens_at": iso(timedelta(hours=-1)),
            "closes_at": iso(timedelta(days=1)),
        },
        headers=as_admin,
    )
    draft = r.json()
    assert client.get(f"/api/v1/ballots/{draft['id']}").status_code == 404
    assert (
        client.post(f"/api/v1/admin/ballots/{draft['id']}/open", headers=as_admin).status_code
        == 422
    )


def test_paid_vote_not_available(client, db, as_admin, seeded):
    r = client.post(
        "/api/v1/admin/ballots",
        json={
            "kind": "special",
            "title": "Payant",
            "opens_at": iso(timedelta(hours=-1)),
            "closes_at": iso(timedelta(days=1)),
            "is_paid": True,
        },
        headers=as_admin,
    )
    assert r.status_code == 422 and r.json()["code"] == "paid_vote_unavailable"


def test_full_vote_flow(client, db, as_admin, sms, seeded):
    ballot = make_ballot(client, as_admin, db)
    option = ballot["options"][0]["id"]
    assert any(b["id"] == ballot["id"] for b in client.get("/api/v1/ballots").json())

    r = client.post(
        f"/api/v1/ballots/{ballot['id']}/code", json={"phone": "70 12 34 56", "choices": [option]}
    )
    assert r.status_code == 200
    assert r.json()["phone_hint"].endswith("34 56") and "7012" not in r.json()["phone_hint"]
    assert sms.sent[-1][0] == "+22670123456"
    challenge = r.json()["challenge_id"]

    bad = client.post(
        f"/api/v1/ballots/{ballot['id']}/vote", json={"challenge_id": challenge, "code": "000000"}
    )
    assert bad.status_code == 422 and bad.json()["code"] == "invalid_code"
    ok = client.post(
        f"/api/v1/ballots/{ballot['id']}/vote",
        json={"challenge_id": challenge, "code": sms.last_code()},
    )
    assert ok.status_code == 204

    # Un code ne sert qu'une fois ; le numéro ne peut plus revoter
    again = client.post(
        f"/api/v1/ballots/{ballot['id']}/vote",
        json={"challenge_id": challenge, "code": sms.last_code()},
    )
    assert again.status_code == 422
    r = client.post(
        f"/api/v1/ballots/{ballot['id']}/code",
        json={"phone": "+226 70 12 34 56", "choices": [option]},
    )
    assert r.status_code == 422 and r.json()["code"] == "already_voted"

    # Résultats publiés en continu (règle « immediate »)
    public = client.get(f"/api/v1/ballots/{ballot['id']}").json()
    assert public["results_visible"] is True
    top = public["results"]["options"][0]
    assert top["option_id"] == option and top["votes"] == 1 and top["share"] == 1.0


def test_input_rules(client, db, as_admin, sms, seeded):
    ballot = make_ballot(client, as_admin, db)
    ids = [o["id"] for o in ballot["options"]]
    url = f"/api/v1/ballots/{ballot['id']}/code"
    r = client.post(url, json={"phone": "+33 6 12 34 56 78", "choices": ids[:1]})
    assert r.json()["code"] == "phone_not_allowed"
    r = client.post(url, json={"phone": "70000001", "choices": ids[:2]})
    assert r.json()["code"] == "invalid_choices"

    upcoming = make_ballot(client, as_admin, db, open_now=False)
    r = client.post(
        f"/api/v1/ballots/{upcoming['id']}/code",
        json={"phone": "70000001", "choices": [upcoming["options"][0]["id"]]},
    )
    assert r.json()["code"] == "ballot_not_open"


def test_attempts_and_rate_limits(client, db, as_admin, sms, seeded):
    ballot = make_ballot(client, as_admin, db)
    choice = [ballot["options"][0]["id"]]
    url = f"/api/v1/ballots/{ballot['id']}"
    challenge = client.post(f"{url}/code", json={"phone": "70000002", "choices": choice}).json()
    code = sms.last_code()
    for _ in range(voting.OTP_MAX_ATTEMPTS):
        client.post(
            f"{url}/vote", json={"challenge_id": challenge["challenge_id"], "code": "111111"}
        )
    r = client.post(f"{url}/vote", json={"challenge_id": challenge["challenge_id"], "code": code})
    assert r.status_code == 422  # le bon code arrive trop tard

    for _ in range(voting.OTP_PER_PHONE[0] - 1):
        client.post(f"{url}/code", json={"phone": "70000002", "choices": choice})
    r = client.post(f"{url}/code", json={"phone": "70000002", "choices": choice})
    assert r.status_code == 429


def test_multiple_choices_single_participation(client, db, as_admin, sms, seeded):
    ballot = make_ballot(client, as_admin, db, max_choices=3, kind="team_of_the_season")
    ids = [o["id"] for o in ballot["options"]]
    assert vote(client, sms, ballot, "70000003", ids[:3]).status_code == 204
    results = client.get(f"/api/v1/ballots/{ballot['id']}").json()["results"]
    assert results["participants"] == 1
    assert sorted(o["votes"] for o in results["options"]) == [0, 0, 1, 1, 1]


def test_mass_voting_flagged_reviewed_and_reported(client, db, as_admin, sms, seeded):
    ballot = make_ballot(client, as_admin, db)
    first = ballot["options"][0]["id"]
    # Même connexion (client de test) : au-delà de 10 votes, les suivants sont mis de côté
    for i in range(12):
        # Numéros distincts et non consécutifs (préfixes différents) : seule la règle IP joue
        assert vote(client, sms, ballot, f"{60 + i}{i:06d}", [first]).status_code == 204

    admin_view = client.get(f"/api/v1/admin/ballots/{ballot['id']}", headers=as_admin).json()
    assert admin_view["flagged_voters"] == 2
    public = client.get(f"/api/v1/ballots/{ballot['id']}").json()
    assert public["results"]["participants"] == 10  # les votes suspects ne comptent pas

    flagged = client.get(
        f"/api/v1/admin/ballots/{ballot['id']}/voters",
        params={"status": "flagged"},
        headers=as_admin,
    ).json()
    assert len(flagged) == 2 and "connexion" in flagged[0]["flag_reason"]
    r = client.post(
        f"/api/v1/admin/ballots/{ballot['id']}/voters/{flagged[0]['voter']}/review",
        json={"decision": "valid"},
        headers=as_admin,
    )
    assert r.json() == {"updated_votes": 1}
    client.post(
        f"/api/v1/admin/ballots/{ballot['id']}/voters/{flagged[1]['voter']}/review",
        json={"decision": "rejected"},
        headers=as_admin,
    )
    assert client.get(f"/api/v1/ballots/{ballot['id']}").json()["results"]["participants"] == 11

    # Journal sans numéro en clair ; le PV porte son empreinte SHA-256
    journal = client.get(f"/api/v1/admin/ballots/{ballot['id']}/journal.csv", headers=as_admin)
    text = journal.content.decode("utf-8-sig")
    assert "+226" not in text and "70000000" not in text and text.count("\n") == 13
    report = client.get(f"/api/v1/admin/ballots/{ballot['id']}/report", headers=as_admin).json()
    assert report["journal_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert (report["valid_voters"], report["flagged_voters"], report["rejected_voters"]) == (
        11,
        0,
        1,
    )


def test_scheduled_results_and_publication(client, db, as_admin, sms, seeded):
    ballot = make_ballot(
        client,
        as_admin,
        db,
        results_visibility="scheduled",
        results_publish_at=iso(timedelta(days=5)),
    )
    vote(client, sms, ballot, "70000009", [ballot["options"][1]["id"]])
    public = client.get(f"/api/v1/ballots/{ballot['id']}").json()
    assert public["results_visible"] is False and public["results"] is None
    url = f"/api/v1/admin/ballots/{ballot['id']}"
    assert client.post(f"{url}/publish", headers=as_admin).status_code == 422  # encore ouvert
    assert client.post(f"{url}/close", headers=as_admin).json()["state"] == "closed"
    assert client.post(f"{url}/publish", headers=as_admin).status_code == 200
    public = client.get(f"/api/v1/ballots/{ballot['id']}").json()
    assert public["results_visible"] is True and public["results"]["participants"] == 1


def test_options_frozen_once_open(client, db, as_admin, sms, seeded):
    ballot = make_ballot(client, as_admin, db)
    r = client.patch(
        f"/api/v1/admin/ballots/{ballot['id']}", json={"options": []}, headers=as_admin
    )
    assert r.status_code == 422
    r = client.patch(
        f"/api/v1/admin/ballots/{ballot['id']}", json={"title": "Nouveau titre"}, headers=as_admin
    )
    assert r.status_code == 200 and r.json()["title"] == "Nouveau titre"


def test_candidates_coaches_and_superadmin_access(client, as_admin, seeded):
    coaches = client.get(
        "/api/v1/admin/ballots/candidates", params={"kind": "coaches"}, headers=as_admin
    ).json()
    assert len(coaches) == 20
    sa = login(client, "superadmin@lds.local")
    assert client.get("/api/v1/admin/ballots", headers=sa).status_code == 200
