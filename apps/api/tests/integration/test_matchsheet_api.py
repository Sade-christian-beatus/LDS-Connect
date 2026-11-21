"""Parcours complet de la feuille de match : composition → soumission → événements → validation."""

import uuid

import pytest
from sqlalchemy import select

from lds_api.models import Match, Pool, Suspension
from lds_api.models.enums import MatchPhase, MatchStatus


@pytest.fixture
def match_id(db, seeded) -> str:
    pool_a = db.scalar(select(Pool).where(Pool.code == "A"))
    m = db.scalar(
        select(Match)
        .where(Match.pool_id == pool_a.id, Match.round_number == 1)
        .order_by(Match.kickoff_at)
    )
    return str(m.id)


def build_lineup(team_sheet: dict, *, locals_wanted: int = 6, subs: int = 7) -> list[dict]:
    """Compose 11 titulaires avec exactement `locals_wanted` locaux, un gardien, un capitaine."""
    cands = [c for c in team_sheet["candidates"] if c["licence_ok"] and not c["is_suspended"]]
    gk = next(c for c in cands if c["position"] == "GK" and c["is_local"])
    field_locals = [c for c in cands if c["is_local"] and c is not gk]
    field_others = [c for c in cands if not c["is_local"] and c["position"] != "GK"]
    starters = [gk, *field_locals[: locals_wanted - 1], *field_others[: 11 - locals_wanted]]
    assert len(starters) == 11, "effectif de démonstration insuffisant pour ce test"
    used = {c["person_id"] for c in starters}
    bench = [c for c in cands if c["person_id"] not in used][:subs]
    entries = [
        {
            "person_id": c["person_id"],
            "role": "starter",
            "shirt_number": c["shirt_number"],
            "is_goalkeeper": c is gk,
            "is_captain": i == 1,
        }
        for i, c in enumerate(starters)
    ]
    entries += [
        {"person_id": c["person_id"], "role": "substitute", "shirt_number": c["shirt_number"]}
        for c in bench
    ]
    return entries


def starters(sheet: dict, side: str) -> list[str]:
    return [e["person_id"] for e in sheet[side]["lineup"] if e["role"] == "starter"]


def subs(sheet: dict, side: str) -> list[str]:
    return [e["person_id"] for e in sheet[side]["lineup"] if e["role"] == "substitute"]


def event(sheet, side, type_, minute, person, related=None, cid=None):
    return {
        "client_uuid": cid or str(uuid.uuid4()),
        "team_id": sheet[side]["team"]["id"],
        "type": type_,
        "minute": minute,
        "person_id": person,
        "related_person_id": related,
    }


def prepare(client, headers, match_id, *, home_locals=6) -> dict:
    url = f"/api/v1/matches/{match_id}/sheet"
    sheet = client.get(url, headers=headers).json()
    for side, locals_wanted in (("home", home_locals), ("away", 6)):
        team_id = sheet[side]["team"]["id"]
        r = client.put(
            f"{url}/lineup/{team_id}",
            json={"entries": build_lineup(sheet[side], locals_wanted=locals_wanted)},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        sheet = r.json()
    return sheet


def test_local_players_rule_blocks_submission(client, as_delegate, match_id):
    sheet = prepare(client, as_delegate, match_id, home_locals=5)
    home = sheet["home"]
    assert home["local_starters"] == 5 and home["local_starters_required"] == 6
    assert [v["code"] for v in home["violations"]] == ["local_players"]

    r = client.post(f"/api/v1/matches/{match_id}/sheet/submit", headers=as_delegate)
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "lineup_invalid"
    assert "Règle des locaux" in next(iter(body["details"].values()))[0]


def test_full_match_flow(client, db, as_delegate, as_admin, match_id):
    url = f"/api/v1/matches/{match_id}/sheet"
    sheet = prepare(client, as_delegate, match_id)
    assert sheet["home"]["violations"] == [] and sheet["away"]["violations"] == []

    # Soumission : compositions verrouillées, match en direct
    r = client.post(f"{url}/submit", headers=as_delegate)
    assert r.status_code == 200, r.text
    sheet = r.json()
    assert sheet["status"] == "submitted" and sheet["match"]["status"] == "live"
    team_id = sheet["home"]["team"]["id"]
    r = client.put(f"{url}/lineup/{team_id}", json={"entries": []}, headers=as_delegate)
    assert r.status_code == 422

    hs, as_ = starters(sheet, "home"), starters(sheet, "away")
    goal = event(sheet, "home", "goal", 12, hs[9], related=hs[8])
    r = client.post(f"{url}/events", json=goal, headers=as_delegate)
    assert r.status_code == 201
    # Rejeu hors ligne du même événement : pas de doublon
    r = client.post(f"{url}/events", json=goal, headers=as_delegate)
    assert len(r.json()["events"]) == 1
    assert r.json()["match"]["home_score"] == 1

    for e in [
        event(sheet, "away", "yellow_card", 30, as_[4]),
        event(sheet, "home", "substitution", 60, hs[9], related=subs(sheet, "home")[0]),
        event(sheet, "away", "own_goal", 70, as_[3]),
        event(sheet, "away", "red_card", 80, as_[5]),
    ]:
        r = client.post(f"{url}/events", json=e, headers=as_delegate)
        assert r.status_code == 201, r.text
    sheet = r.json()
    assert (sheet["match"]["home_score"], sheet["match"]["away_score"]) == (2, 0)
    assert sheet["match"]["live_minute"] == 80

    # Incohérence : le joueur remplacé ne peut plus marquer
    r = client.post(
        f"{url}/events", json=event(sheet, "home", "goal", 85, hs[9]), headers=as_delegate
    )
    assert r.status_code == 422 and "pas sur le terrain" in r.json()["detail"]

    # Suppression refusée si elle rend la suite incohérente (le remplaçant a joué ? non : ok)
    sub_event = next(e for e in sheet["events"] if e["type"] == "substitution")
    late_goal = event(sheet, "home", "goal", 88, sub_event["related_person_id"])
    client.post(f"{url}/events", json=late_goal, headers=as_delegate)
    r = client.delete(f"{url}/events/{sub_event['id']}", headers=as_delegate)
    assert r.status_code == 422 and r.json()["code"] == "event_dependency"

    # Validation : score officiel, classement, suspension automatique (rouge)
    r = client.post(f"{url}/validate", headers=as_delegate)
    assert r.status_code == 200, r.text
    sheet = r.json()
    assert sheet["status"] == "validated"
    assert sheet["match"]["status"] == "finished"
    assert (sheet["match"]["home_score"], sheet["match"]["away_score"]) == (3, 0)

    table = client.get("/api/v1/standings").json()[0]["rows"]
    leader = table[0]
    assert leader["team"]["id"] == sheet["home"]["team"]["id"] and leader["points"] == 3

    susp = db.scalar(select(Suspension).where(Suspension.person_id == uuid.UUID(as_[5])))
    assert susp is not None and susp.reason.value == "red_card" and susp.matches_count == 1

    # Feuille verrouillée ; clôture réservée à l'administration
    r = client.post(
        f"{url}/events", json=event(sheet, "home", "goal", 89, hs[1]), headers=as_delegate
    )
    assert r.status_code == 422
    assert client.post(f"{url}/close", headers=as_delegate).status_code == 403
    r = client.post(f"{url}/close", headers=as_admin)
    assert r.status_code == 200 and r.json()["status"] == "closed"


def test_suspended_player_rejected_in_next_lineup(client, db, as_delegate, match_id):
    url = f"/api/v1/matches/{match_id}/sheet"
    sheet = prepare(client, as_delegate, match_id)
    client.post(f"{url}/submit", headers=as_delegate)
    red = starters(sheet, "home")[3]
    client.post(
        f"{url}/events", json=event(sheet, "home", "red_card", 20, red), headers=as_delegate
    )
    assert client.post(f"{url}/validate", headers=as_delegate).status_code == 200

    team_id = sheet["home"]["team"]["id"]
    nxt = db.scalar(
        select(Match).where(
            Match.phase == MatchPhase.GROUP,
            Match.round_number == 2,
            (Match.home_team_id == uuid.UUID(team_id)) | (Match.away_team_id == uuid.UUID(team_id)),
        )
    )
    s2 = client.get(f"/api/v1/matches/{nxt.id}/sheet", headers=as_delegate).json()
    side = "home" if s2["home"]["team"]["id"] == team_id else "away"
    cand = next(c for c in s2[side]["candidates"] if c["person_id"] == red)
    assert cand["is_suspended"] is True


def test_club_manager_cannot_edit_sheet(client, as_club, match_id):
    r = client.get(f"/api/v1/matches/{match_id}/sheet", headers=as_club)
    assert r.status_code == 403


def test_reopen_before_kickoff(client, as_delegate, match_id):
    url = f"/api/v1/matches/{match_id}/sheet"
    prepare(client, as_delegate, match_id)
    client.post(f"{url}/submit", headers=as_delegate)
    r = client.post(f"{url}/reopen", headers=as_delegate)
    assert r.status_code == 200
    assert r.json()["status"] == "draft" and r.json()["match"]["status"] == "scheduled"


def test_delegate_match_list(client, as_delegate, seeded):
    r = client.get("/api/v1/delegate/matches", params={"all": True}, headers=as_delegate)
    assert r.status_code == 200
    assert len(r.json()) == 90  # cases du tableau final sans équipes exclues
    assert r.json()[0]["sheet_status"] is None


def test_knockout_draw_requires_penalties(client, db, as_admin, seeded):
    qf = db.scalar(select(Match).where(Match.bracket_slot == "QF1"))
    group = db.scalar(select(Match).where(Match.phase == MatchPhase.GROUP))
    qf.home_team_id, qf.away_team_id = group.home_team_id, group.away_team_id
    qf.kickoff_at = group.kickoff_at
    qf.status = MatchStatus.SCHEDULED
    db.flush()

    url = f"/api/v1/matches/{qf.id}/sheet"
    prepare(client, as_admin, str(qf.id))
    assert client.post(f"{url}/submit", headers=as_admin).status_code == 200
    r = client.post(f"{url}/validate", headers=as_admin)
    assert r.status_code == 422 and r.json()["code"] == "penalties_required"
    client.patch(url, json={"home_penalties": 4, "away_penalties": 3}, headers=as_admin)
    r = client.post(f"{url}/validate", headers=as_admin)
    assert r.status_code == 200, r.text
    assert r.json()["match"]["home_penalties"] == 4
