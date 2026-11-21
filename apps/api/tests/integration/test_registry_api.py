from sqlalchemy import select

from lds_api.models import AuditLog, Region, Team

PLAYER = {
    "first_name": "Test",
    "last_name": "Joueur",
    "birth_date": "2005-03-10",
    "position": "MF",
    "cnib_number": "X11112222",
    "phone": "+226 00 11 22 33",
}


def team(db, short: str) -> Team:
    return db.scalar(select(Team).where(Team.short_name == short))


def test_public_teams_list(client, seeded):
    teams = client.get("/api/v1/teams").json()
    assert len(teams) == 20
    assert {t["pool_code"] for t in teams} == {"A", "B"}


def test_public_team_detail_hides_personal_data(client, seeded):
    r = client.get("/api/v1/teams/vinnim-du-kadiogo")
    assert r.status_code == 200
    body = r.json()
    assert len(body["players"]) == 30 and len(body["staff"]) == 7
    player = body["players"][0]
    assert set(player) == {"display_name", "position", "age", "shirt_number"}
    raw = r.text
    for forbidden in ("birth_date", "cnib", "phone", "first_name", "last_name"):
        assert forbidden not in raw


def test_squad_requires_auth_and_scope(client, db, as_club, as_admin):
    vinnim, nanga = team(db, "Vinnim"), team(db, "Nanga")
    assert client.get(f"/api/v1/admin/teams/{vinnim.id}/squad").status_code == 401
    assert client.get(f"/api/v1/admin/teams/{vinnim.id}/squad", headers=as_club).status_code == 200
    r = client.get(f"/api/v1/admin/teams/{nanga.id}/squad", headers=as_club)
    assert r.status_code == 403
    r = client.get(f"/api/v1/admin/teams/{nanga.id}/squad", headers=as_admin)
    assert r.status_code == 200
    squad = r.json()
    assert {c["code"] for c in squad["compliance"]} >= {"max_players", "youth_quota"}
    assert all(c["ok"] for c in squad["compliance"])
    assert any(m["is_local"] for m in squad["members"] if m["kind"] == "player")


def test_squad_full_rejects_31st_player(client, db, as_club):
    vinnim = team(db, "Vinnim")
    r = client.post(f"/api/v1/admin/teams/{vinnim.id}/players", json=PLAYER, headers=as_club)
    assert r.status_code == 422
    assert r.json()["code"] == "squad_full"


def test_create_player_after_release(client, db, as_club):
    vinnim = team(db, "Vinnim")
    squad = client.get(f"/api/v1/admin/teams/{vinnim.id}/squad", headers=as_club).json()
    leaving = next(m for m in squad["members"] if m["kind"] == "player")
    r = client.post(f"/api/v1/admin/persons/{leaving['person_id']}/release", headers=as_club)
    assert r.status_code == 204

    r = client.post(f"/api/v1/admin/teams/{vinnim.id}/players", json=PLAYER, headers=as_club)
    assert r.status_code == 201, r.text
    person_id = r.json()["person_id"]

    # Doublon de CNIB refusé (même avec un format différent)
    vinnim_squad = client.get(f"/api/v1/admin/teams/{vinnim.id}/squad", headers=as_club).json()
    other = next(m for m in vinnim_squad["members"] if m["kind"] == "player")
    r = client.patch(
        f"/api/v1/admin/players/{other['person_id']}",
        json={"cnib_number": "x 1111-2222"},
        headers=as_club,
    )
    assert r.status_code == 422 and r.json()["code"] == "duplicate_cnib"

    # Lecture des données sensibles : autorisée et journalisée
    r = client.get(f"/api/v1/admin/persons/{person_id}/sensitive", headers=as_club)
    assert r.json() == {
        "person_id": person_id,
        "cnib_number": "X11112222",
        "phone": "+226 00 11 22 33",
    }
    log = db.scalar(select(AuditLog).where(AuditLog.action == "read_sensitive"))
    assert log.entity_id == person_id


def test_min_age_enforced(client, db, as_admin):
    nanga = team(db, "Nanga")
    squad = client.get(f"/api/v1/admin/teams/{nanga.id}/squad", headers=as_admin).json()
    leaving = next(m for m in squad["members"] if m["kind"] == "player")
    client.post(f"/api/v1/admin/persons/{leaving['person_id']}/release", headers=as_admin)
    too_young = {**PLAYER, "birth_date": "2011-06-01", "cnib_number": None}
    r = client.post(f"/api/v1/admin/teams/{nanga.id}/players", json=too_young, headers=as_admin)
    assert r.status_code == 422 and r.json()["code"] == "min_age"


def test_update_player_is_audited_without_secrets(client, db, as_admin):
    vinnim = team(db, "Vinnim")
    kadiogo = db.scalar(select(Region).where(Region.name == "Kadiogo"))
    squad = client.get(f"/api/v1/admin/teams/{vinnim.id}/squad", headers=as_admin).json()
    p = next(m for m in squad["members"] if m["kind"] == "player" and m["position"] != "GK")
    r = client.patch(
        f"/api/v1/admin/players/{p['person_id']}",
        json={
            "position": "GK",
            "phone": "+226 00 99 99 99",
            "residence_region_id": str(kadiogo.id),
        },
        headers=as_admin,
    )
    assert r.status_code == 204
    log = db.scalar(
        select(AuditLog).where(AuditLog.action == "update", AuditLog.entity_id == p["person_id"])
    )
    assert log.changes["phone"] == ["***", "***"]
    assert log.changes["position"][1] == "GK"


def test_controller_cannot_read_squads(client, db, as_controller):
    vinnim = team(db, "Vinnim")
    r = client.get(f"/api/v1/admin/teams/{vinnim.id}/squad", headers=as_controller)
    assert r.status_code == 403
