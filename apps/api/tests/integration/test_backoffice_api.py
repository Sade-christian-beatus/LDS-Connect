from sqlalchemy import select

from lds_api.models import Licence, Team
from lds_api.models.enums import LicenceStatus


def test_overview_admin_sees_all_compliant(client, as_admin):
    r = client.get("/api/v1/admin/teams/overview", headers=as_admin)
    assert r.status_code == 200
    teams = r.json()
    assert len(teams) == 20
    first = teams[0]
    assert first["players"] == 30 and first["staff"] == 7
    assert first["licences_active"] == 37 and first["licences_missing"] == 0
    assert first["youth_players"] >= 7
    assert all(t["compliant"] for t in teams), [t["issues"] for t in teams if t["issues"]]


def test_overview_club_sees_only_its_team_and_issues(client, db, as_club):
    vinnim = db.scalar(select(Team).where(Team.short_name == "Vinnim"))
    lic = db.scalar(
        select(Licence)
        .join(Licence.membership)
        .where(Licence.status == LicenceStatus.ACTIVE)
        .where(Licence.membership.has(team_id=vinnim.id))
    )
    lic.status = LicenceStatus.SUSPENDED
    db.flush()
    r = client.get("/api/v1/admin/teams/overview", headers=as_club)
    assert [t["team"]["short_name"] for t in r.json()] == ["Vinnim"]
    t = r.json()[0]
    assert t["licences_blocked"] == 1 and not t["compliant"]
    assert any("suspendue" in i for i in t["issues"])


def test_squad_member_has_edit_fields(client, db, as_admin):
    vinnim = db.scalar(select(Team).where(Team.short_name == "Vinnim"))
    members = client.get(f"/api/v1/admin/teams/{vinnim.id}/squad", headers=as_admin).json()[
        "members"
    ]
    player = next(m for m in members if m["kind"] == "player")
    assert player["residence_region_id"] and player["nationality"] == "BF"
    assert isinstance(player["is_minor"], bool)
    assert any(m["is_minor"] for m in members)


def test_regions_public(client, seeded):
    r = client.get("/api/v1/regions")
    assert len(r.json()) == 17


def test_audit_log_filters_and_permissions(client, as_admin, as_club, as_delegate):
    assert client.get("/api/v1/admin/audit", headers=as_club).status_code == 403
    r = client.get("/api/v1/admin/audit", params={"action": "login"}, headers=as_admin)
    entries = r.json()
    assert entries and all(e["action"] == "login" for e in entries)
    ids = [e["id"] for e in entries]
    assert ids == sorted(ids, reverse=True)
    older = client.get("/api/v1/admin/audit", params={"before_id": ids[0]}, headers=as_admin).json()
    assert all(e["id"] < ids[0] for e in older)
