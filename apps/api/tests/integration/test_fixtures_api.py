from collections import Counter

from sqlalchemy import select

from lds_api.models import Match, Pool
from lds_api.models.enums import MatchPhase, MatchStatus
from lds_api.services import fixtures, seasons, standings


def pool(db, code) -> Pool:
    return db.scalar(select(Pool).where(Pool.code == code))


def test_seeded_calendar_shape(client, seeded):
    matches = client.get("/api/v1/matches", params={"pool": "A"}).json()
    assert len(matches) == 45
    assert Counter(m["round_number"] for m in matches) == dict.fromkeys(range(1, 10), 5)
    assert all(m["venue"]["city"] == "Ouagadougou" for m in matches)
    teams = Counter(t for m in matches for t in (m["home"]["slug"], m["away"]["slug"]))
    assert set(teams.values()) == {9}
    pool_b = client.get("/api/v1/matches", params={"pool": "B"}).json()
    assert all(m["venue"]["city"] == "Bobo-Dioulasso" for m in pool_b)


def test_matches_filter_by_team_and_round(client, seeded):
    r = client.get("/api/v1/matches", params={"team": "soum-fc"}).json()
    assert len(r) == 9
    r = client.get("/api/v1/matches", params={"pool": "B", "round": 1}).json()
    assert len(r) == 5


def test_regeneration_requires_force_and_is_blocked_once_started(client, db, as_admin):
    a = pool(db, "A")
    url = f"/api/v1/admin/pools/{a.id}/fixtures"
    r = client.post(url, json={}, headers=as_admin)
    assert r.status_code == 422 and r.json()["code"] == "fixtures_exist"

    r = client.post(
        url, json={"force": True, "seed": 11, "first_date": "2027-01-16"}, headers=as_admin
    )
    assert r.status_code == 201 and len(r.json()) == 45
    assert r.json()[0]["kickoff_at"].startswith("2027-01-16T15:00")

    m = db.scalar(select(Match).where(Match.pool_id == a.id))
    m.status = MatchStatus.LIVE
    db.flush()
    r = client.post(url, json={"force": True}, headers=as_admin)
    assert r.status_code == 422 and r.json()["code"] == "fixtures_locked"


def test_generation_forbidden_for_club(client, db, as_club):
    r = client.post(f"/api/v1/admin/pools/{pool(db, 'A').id}/fixtures", json={}, headers=as_club)
    assert r.status_code == 403


def test_admin_updates_venue_and_kickoff(client, db, as_admin):
    m = client.get("/api/v1/matches", params={"pool": "A", "round": 1}).json()[0]
    r = client.post(
        "/api/v1/admin/venues",
        json={"name": "Stade de test", "city": "Ouagadougou", "is_confirmed": True},
        headers=as_admin,
    )
    venue_id = r.json()["id"]
    r = client.patch(
        f"/api/v1/admin/matches/{m['id']}",
        json={"venue_id": venue_id, "kickoff_at": "2027-01-10T16:00:00Z"},
        headers=as_admin,
    )
    assert r.status_code == 200
    assert r.json()["venue"]["name"] == "Stade de test"
    r = client.patch(
        f"/api/v1/admin/matches/{m['id']}", json={"status": "finished"}, headers=as_admin
    )
    assert r.status_code == 422 and r.json()["code"] == "use_sheet"


def _finish_pool(db, code: str) -> None:
    """Termine tous les matchs d'une poule : le premier de la liste de tirage gagne tout."""
    p = pool(db, code)
    for i, m in enumerate(
        db.scalars(select(Match).where(Match.pool_id == p.id, Match.phase == MatchPhase.GROUP))
    ):
        m.status = MatchStatus.FINISHED
        m.home_score, m.away_score = (i % 4, (i * 7) % 3)
    db.flush()
    standings.invalidate(p.id)


def test_standings_after_results(client, db, seeded):
    empty = client.get("/api/v1/standings").json()
    assert [p["pool_code"] for p in empty] == ["A", "B"]
    assert all(r["points"] == 0 and r["needs_draw"] for r in empty[0]["rows"])

    _finish_pool(db, "A")
    a = client.get("/api/v1/standings").json()[0]
    assert a["matches_played"] == a["matches_total"] == 45
    assert all(r["played"] == 9 for r in a["rows"])
    pts = [r["points"] for r in a["rows"]]
    assert pts == sorted(pts, reverse=True)
    assert sum(r["qualified_zone"] for r in a["rows"]) == 4
    assert sum(r["goal_difference"] for r in a["rows"]) == 0


def test_bracket_filled_when_group_stage_complete(client, db, seeded, as_admin):
    bracket = client.get("/api/v1/bracket").json()
    assert [m["bracket_slot"] for m in bracket] == [
        "QF1",
        "QF2",
        "QF3",
        "QF4",
        "SF1",
        "SF2",
        "P3",
        "F",
    ]
    assert bracket[0]["home"] is None

    _finish_pool(db, "A")
    _finish_pool(db, "B")
    fixtures.refresh_knockout(db, seasons.current_season(db))
    bracket = client.get("/api/v1/bracket").json()
    a = client.get("/api/v1/standings").json()[0]
    b = client.get("/api/v1/standings").json()[1]
    qf1 = bracket[0]
    assert qf1["home"]["id"] == a["rows"][0]["team"]["id"]
    assert qf1["away"]["id"] == b["rows"][3]["team"]["id"]
    assert (
        bracket[4]["home"] is None
    )  # demi-finales inconnues tant que les quarts ne sont pas joués
