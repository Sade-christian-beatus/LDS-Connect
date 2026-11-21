from datetime import date

from sqlalchemy import select

from lds_api.domain.signed_token import b64url_decode
from lds_api.models import Team
from lds_api.services import licences


def vinnim(db) -> Team:
    return db.scalar(select(Team).where(Team.short_name == "Vinnim"))


def issue_team(client, db, headers):
    t = vinnim(db)
    r = client.post(f"/api/v1/admin/teams/{t.id}/licences/issue-all", headers=headers)
    assert r.status_code == 200, r.text
    return t, r.json()


def test_public_keys_are_exposed_without_auth(client, seeded):
    r = client.get("/api/v1/licences/public-keys")
    assert r.status_code == 200
    key = r.json()["keys"][0]
    assert key["alg"] == "Ed25519" and len(b64url_decode(key["x"])) == 32
    assert "max-age" in r.headers["cache-control"]


def test_issue_all_and_verify(client, db, as_admin, as_controller):
    # Le seed de démonstration a déjà délivré les 37 licences : rien de plus à émettre
    t, result = issue_team(client, db, as_admin)
    assert result == {"issued": 0, "errors": []}

    lics = client.get(f"/api/v1/admin/teams/{t.id}/licences", headers=as_admin).json()
    assert len(lics) == 37
    assert lics[0]["number"].startswith("LDS27-")
    token = lics[0]["token"]

    # Le QR ne contient ni date de naissance ni CNIB
    payload = licences.signed_token.verify(
        token, licences.public_keys(), prefix=licences.signed_token.LICENCE_PREFIX
    )
    assert set(payload) <= {"kid", "n", "s", "nm", "tm", "r", "vf", "vu", "no"}

    # Avant le début de saison (aujourd'hui : novembre 2026), la licence n'est pas encore valide
    r = client.post("/api/v1/licences/verify", json={"token": token}, headers=as_controller)
    assert r.status_code == 200
    body = r.json()
    if date.today() < date(2027, 1, 1):
        assert body["valid"] is False and "pas encore valide" in body["reason"]
    assert body["holder"]["tm"] == "Vinnim"
    assert licences.verify(db, token, on=date(2027, 3, 1)).valid is True


def test_issue_requires_permission(client, db, as_club):
    t = vinnim(db)
    r = client.post(f"/api/v1/admin/teams/{t.id}/licences/issue-all", headers=as_club)
    assert r.status_code == 403


def test_suspended_licence_fails_verification_and_is_listed(client, db, as_admin, as_controller):
    t, _ = issue_team(client, db, as_admin)
    lic = client.get(f"/api/v1/admin/teams/{t.id}/licences", headers=as_admin).json()[0]
    r = client.post(
        f"/api/v1/admin/licences/{lic['id']}/status",
        json={"status": "suspended", "reason": "Pièce d'identité à vérifier"},
        headers=as_admin,
    )
    assert r.status_code == 200
    v = client.post("/api/v1/licences/verify", json={"token": lic["token"]}, headers=as_controller)
    assert v.json()["valid"] is False and v.json()["status"] == "suspended"
    entries = client.get("/api/v1/licences/status-list", headers=as_controller).json()["entries"]
    assert {"n": lic["number"], "status": "suspended"}.items() <= entries[0].items()


def test_forged_token_rejected(client, db, as_admin, as_controller):
    t, _ = issue_team(client, db, as_admin)
    token = client.get(f"/api/v1/admin/teams/{t.id}/licences", headers=as_admin).json()[0]["token"]
    prefix, body, sig = token.split(".")
    forged = f"{prefix}.{body[:-2]}xx.{sig}"
    r = client.post("/api/v1/licences/verify", json={"token": forged}, headers=as_controller)
    assert r.json()["valid"] is False


def test_out_of_period(db, client, as_admin):
    t, _ = issue_team(client, db, as_admin)
    token = client.get(f"/api/v1/admin/teams/{t.id}/licences", headers=as_admin).json()[0]["token"]
    assert licences.verify(db, token, on=date(2027, 3, 1)).valid is True
    expired = licences.verify(db, token, on=date(2027, 7, 1))
    assert expired.valid is False and expired.reason == "Licence expirée"


def test_qr_svg(client, db, as_admin, as_club):
    t, _ = issue_team(client, db, as_admin)
    lic = client.get(f"/api/v1/admin/teams/{t.id}/licences", headers=as_club).json()[0]
    r = client.get(f"/api/v1/admin/licences/{lic['id']}/qr.svg", headers=as_club)
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    assert r.text.startswith("<svg") and 'xmlns="http://www.w3.org/2000/svg"' in r.text


def test_issue_for_new_player_and_released_player_revoked(client, db, as_admin):
    t = vinnim(db)
    squad = client.get(f"/api/v1/admin/teams/{t.id}/squad", headers=as_admin).json()
    leaving = next(m for m in squad["members"] if m["kind"] == "player")
    client.post(f"/api/v1/admin/persons/{leaving['person_id']}/release", headers=as_admin)
    status = client.post(
        "/api/v1/licences/verify", json={"token": leaving_token(db, leaving)}, headers=as_admin
    ).json()["status"]
    assert status == "revoked"

    new = {
        "first_name": "Nouveau",
        "last_name": "Joueur",
        "birth_date": "2008-05-05",
        "position": "FW",
    }
    created = client.post(f"/api/v1/admin/teams/{t.id}/players", json=new, headers=as_admin).json()
    r = client.post(
        "/api/v1/admin/licences/issue",
        json={"membership_id": created["membership_id"]},
        headers=as_admin,
    )
    assert r.status_code == 200, r.text
    assert r.json()["number"] == "LDS27-00741"


def leaving_token(db, member) -> str:
    from lds_api.models import Licence

    return db.scalar(select(Licence.token).where(Licence.person_id == member["person_id"]))
