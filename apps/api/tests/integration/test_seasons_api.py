"""Règles de la saison (M1), saisons (M2), stades (M3)."""

from sqlalchemy import select, update

from lds_api.models import AuditLog, Match, Season, Venue
from lds_api.models.enums import MatchStatus


def test_rules_read_and_update(client, db, as_admin, as_club):
    assert client.get("/api/v1/admin/rules", headers=as_club).status_code == 403
    rules = client.get("/api/v1/admin/rules", headers=as_admin).json()
    assert rules["points_win"] == 3 and "points" in rules["tiebreakers"]

    r = client.patch(
        "/api/v1/admin/rules",
        json={"max_staff": rules["max_staff"] + 1, "reason": "Décision du bureau"},
        headers=as_admin,
    )
    assert r.status_code == 200, r.text
    assert r.json()["max_staff"] == rules["max_staff"] + 1
    log = db.scalars(select(AuditLog).where(AuditLog.action == "update_rules")).all()[-1]
    assert log.changes["reason"] == "Décision du bureau"
    assert log.changes["max_staff"] == [rules["max_staff"], rules["max_staff"] + 1]

    # Contrôles de cohérence
    for bad in (
        {"tiebreakers": ["points", "inconnu"]},
        {"points_win": 1, "points_draw": 1},
        {"knockout_pairings": [["A1", "A1"]]},
        {"prize_money": {"1": -5}},
    ):
        r = client.patch("/api/v1/admin/rules", json={**bad, "reason": "essai"}, headers=as_admin)
        assert r.status_code == 422, (bad, r.text)


def test_ranking_rules_locked_once_season_started(client, db, as_admin, seeded):
    db.execute(
        update(Match).where(Match.season_id == seeded.id).values(status=MatchStatus.SCHEDULED)
    )
    db.commit()
    r = client.patch(
        "/api/v1/admin/rules", json={"points_win": 4, "reason": "Avant saison"}, headers=as_admin
    )
    assert r.status_code == 200 and r.json()["season_started"] is False

    m = db.scalar(select(Match).where(Match.season_id == seeded.id).limit(1))
    m.status = MatchStatus.FINISHED
    db.commit()
    r = client.patch(
        "/api/v1/admin/rules", json={"points_win": 3, "reason": "En cours"}, headers=as_admin
    )
    assert r.status_code == 422 and r.json()["code"] == "rules_locked"
    body = client.get("/api/v1/admin/rules", headers=as_admin).json()
    assert body["season_started"] and "points_win" in body["locked_fields"]
    # Les règles administratives restent modifiables
    r = client.patch(
        "/api/v1/admin/rules", json={"max_substitutions": 4, "reason": "Saison"}, headers=as_admin
    )
    assert r.status_code == 200


def test_create_and_activate_season(client, db, as_admin, seeded):
    from .conftest import login

    superadmin = login(client, "superadmin@lds.local")
    body = {
        "year": seeded.year + 1,
        "name": f"Saison {seeded.year + 1}",
        "starts_on": f"{seeded.year + 1}-01-01",
        "ends_on": f"{seeded.year + 1}-06-30",
    }
    r = client.post("/api/v1/admin/seasons", json=body, headers=superadmin)
    assert r.status_code == 201, r.text
    new = r.json()
    assert new["status"] == "draft" and not new["is_current"] and new["teams"] == 20
    assert client.post("/api/v1/admin/seasons", json=body, headers=superadmin).status_code == 422

    listing = client.get("/api/v1/admin/seasons", headers=superadmin).json()
    assert [x["year"] for x in listing][:2] == [seeded.year + 1, seeded.year]

    db.execute(update(Match).values(status=MatchStatus.SCHEDULED))
    db.commit()
    r = client.post(f"/api/v1/admin/seasons/{new['id']}/activate", headers=superadmin)
    assert r.status_code == 200 and r.json()["is_current"]
    db.expire_all()
    old = db.get(Season, seeded.id)
    assert old.is_current is False and old.status == "closed"
    # La nouvelle saison a ses propres règles et ses poules
    assert client.get("/api/v1/admin/rules", headers=superadmin).json()["season_id"] == new["id"]
    # Une saison close ne revient pas
    r = client.post(f"/api/v1/admin/seasons/{seeded.id}/activate", headers=superadmin)
    assert r.status_code == 422


def test_update_venue(client, db, as_admin, as_club, seeded):
    v = db.scalar(select(Venue).where(Venue.is_confirmed.is_(False)).limit(1)) or db.scalar(
        select(Venue).limit(1)
    )
    url = f"/api/v1/admin/venues/{v.id}"
    assert client.patch(url, json={"is_confirmed": True}, headers=as_club).status_code == 403
    r = client.patch(url, json={"is_confirmed": True, "capacity": 25000}, headers=as_admin)
    assert r.status_code == 200, r.text
    assert r.json()["is_confirmed"] and r.json()["capacity"] == 25000
    other = db.scalar(select(Venue).where(Venue.id != v.id).limit(1))
    if other:
        assert client.patch(url, json={"name": other.name}, headers=as_admin).status_code == 422
