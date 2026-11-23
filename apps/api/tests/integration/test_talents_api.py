"""Talents : statistiques recalculées à la validation, tableau de bord, fiche publique, suivi
et notes internes (chiffrées, consultation journalisée)."""

import pytest
from sqlalchemy import select, text

from lds_api.models import AuditLog, PlayerStat, TalentNote

from .conftest import login
from .test_matchsheet_api import event, prepare, starters, subs


@pytest.fixture
def as_scout(client):
    return login(client, "technique@lds.local")


@pytest.fixture
def played(client, as_delegate, match_id):
    """Un match validé : but (passe), remplacement à la 60e, carton jaune."""
    url = f"/api/v1/matches/{match_id}/sheet"
    sheet = prepare(client, as_delegate, match_id)
    sheet = client.post(f"{url}/submit", headers=as_delegate).json()
    hs, as_ = starters(sheet, "home"), starters(sheet, "away")
    sub_in = subs(sheet, "home")[0]
    for e in [
        event(sheet, "home", "goal", 12, hs[9], related=hs[8]),
        event(sheet, "away", "yellow_card", 30, as_[4]),
        event(sheet, "home", "substitution", 60, hs[9], related=sub_in),
    ]:
        assert client.post(f"{url}/events", json=e, headers=as_delegate).status_code == 201
    r = client.post(f"{url}/validate", headers=as_delegate)
    assert r.status_code == 200, r.text
    return {
        "sheet": r.json(),
        "scorer": hs[9],
        "passer": hs[8],
        "sub_in": sub_in,
        "home_gk": hs[0],
        "away_gk": as_[0],
        "booked": as_[4],
    }


def test_stats_computed_at_validation(db, played):
    stats = {str(s.person_id): s for s in db.scalars(select(PlayerStat))}
    scorer, sub_in = stats[played["scorer"]], stats[played["sub_in"]]
    assert (scorer.goals, scorer.starts, scorer.minutes_played) == (1, 1, 60)
    assert (sub_in.appearances, sub_in.starts, sub_in.minutes_played) == (1, 0, 30)
    assert stats[played["passer"]].assists == 1
    assert stats[played["booked"]].yellow_cards == 1
    assert stats[played["home_gk"]].clean_sheets == 1
    assert stats[played["away_gk"]].clean_sheets == 0
    assert stats[played["home_gk"]].minutes_played == 90  # durée des règles de la saison


def test_dashboard_filters_and_permissions(client, as_scout, as_club, as_delegate, played):
    assert client.get("/api/v1/admin/talents", headers=as_club).status_code == 403
    assert client.get("/api/v1/admin/talents", headers=as_delegate).status_code == 403

    r = client.get("/api/v1/admin/talents", params={"sort": "goals", "limit": 5}, headers=as_scout)
    assert r.status_code == 200, r.text
    data = r.json()
    top = data["rows"][0]
    assert top["person_id"] == played["scorer"] and top["goals"] == 1
    assert "birth_date" not in top and data["match_duration_minutes"] == 90
    assert data["total"] > 500  # tous les joueurs des effectifs, même sans match joué

    fw = client.get(
        "/api/v1/admin/talents", params={"position": "FW", "limit": 800}, headers=as_scout
    ).json()
    assert fw["rows"] and all(r["position"] == "FW" for r in fw["rows"])
    young = client.get(
        "/api/v1/admin/talents", params={"age_max": 18, "limit": 800}, headers=as_scout
    ).json()
    assert young["rows"] and all(r["age"] <= 18 and r["is_youth"] for r in young["rows"])
    played_only = client.get(
        "/api/v1/admin/talents", params={"min_minutes": 1, "limit": 800}, headers=as_scout
    ).json()
    assert 0 < played_only["total"] <= 36
    team_id = played["sheet"]["home"]["team"]["id"]
    team = client.get(
        "/api/v1/admin/talents", params={"team_id": team_id, "limit": 800}, headers=as_scout
    ).json()
    assert {r["team"]["id"] for r in team["rows"]} == {team_id}

    csv = client.get("/api/v1/admin/talents.csv", params={"position": "GK"}, headers=as_scout)
    assert csv.status_code == 200 and csv.text.startswith("﻿team;full_name")


def test_public_player_page_shows_allowed_data_only(client, played):
    r = client.get(f"/api/v1/players/{played['scorer']}")
    assert r.status_code == 200, r.text
    p = r.json()
    assert set(p) == {
        "person_id",
        "display_name",
        "position",
        "age",
        "shirt_number",
        "team",
        "stats",
        "matches",
    }
    assert p["stats"]["goals"] == 1 and p["matches"][0]["minutes"] == 60
    # Les équipes publiques donnent le lien vers la fiche
    slug = p["team"]["slug"]
    players = client.get(f"/api/v1/teams/{slug}").json()["players"]
    assert any(x["person_id"] == played["scorer"] for x in players)


def test_watchlist_and_encrypted_notes(client, db, as_scout, as_admin, played):
    pid = played["scorer"]
    r = client.put(
        f"/api/v1/admin/talents/{pid}/watch",
        json={"watched": True, "tags": ["Sélection U20"]},
        headers=as_scout,
    )
    assert r.status_code == 204
    r = client.post(
        f"/api/v1/admin/talents/{pid}/notes",
        json={"body": "Très bon appel en profondeur, pied gauche à travailler.", "rating": 4},
        headers=as_scout,
    )
    assert r.status_code == 201

    prof = client.get(f"/api/v1/admin/talents/{pid}", headers=as_admin).json()
    assert prof["watched"] and prof["tags"] == ["Sélection U20"]
    assert prof["notes"][0]["body"].startswith("Très bon appel") and prof["notes"][0]["rating"] == 4
    assert prof["notes"][0]["author"] == "Cellule technique (démo)"

    # Texte chiffré en base, absent du journal ; la consultation est journalisée
    raw = db.execute(text("SELECT body FROM talent_notes")).scalar_one()
    assert b"profondeur" not in bytes(raw)
    reads = db.scalars(
        select(AuditLog).where(AuditLog.entity_type == "talent_notes", AuditLog.action == "read")
    ).all()
    assert reads
    assert all("profondeur" not in str(a.changes) for a in db.scalars(select(AuditLog)))

    dash = client.get(
        "/api/v1/admin/talents", params={"watched_only": True}, headers=as_scout
    ).json()
    assert [r["person_id"] for r in dash["rows"]] == [pid] and dash["rows"][0]["avg_rating"] == 4.0

    note_id = prof["notes"][0]["id"]
    r = client.post(
        f"/api/v1/admin/talent-notes/{note_id}/delete",
        json={"reason": "Erreur de joueur"},
        headers=as_scout,
    )
    assert r.status_code == 204
    assert client.get(f"/api/v1/admin/talents/{pid}", headers=as_scout).json()["notes"] == []
    assert db.get(TalentNote, prof["notes"][0]["id"]).deleted_reason == "Erreur de joueur"


def test_notes_are_not_for_club_managers(client, as_club, played):
    pid = played["scorer"]
    assert client.get(f"/api/v1/admin/talents/{pid}", headers=as_club).status_code == 403
    r = client.post(f"/api/v1/admin/talents/{pid}/notes", json={"body": "test"}, headers=as_club)
    assert r.status_code == 403
