from sqlalchemy import select

from lds_api.models import AuditLog, Match, Pool, Team, User

from .conftest import DEMO_PASSWORD, login


def _login_raw(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_only_super_admin_manages_accounts(client, as_admin, seeded):
    assert client.get("/api/v1/admin/users", headers=as_admin).status_code == 403
    sa = login(client, "superadmin@lds.local")
    users = client.get("/api/v1/admin/users", headers=sa).json()
    assert len(users) == 6
    assert all("password_hash" not in u and "$argon2" not in str(u) for u in users)


def test_create_user_with_temporary_password(client, db, seeded):
    sa = login(client, "superadmin@lds.local")
    r = client.post(
        "/api/v1/admin/users",
        json={
            "email": "Nouveau.Delegue@exemple.bf",
            "full_name": "Nouveau Délégué",
            "role": "delegue_match",
        },
        headers=sa,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    temp = body["temporary_password"]
    assert len(temp) >= 16 and body["user"]["email"] == "nouveau.delegue@exemple.bf"
    assert _login_raw(client, "nouveau.delegue@exemple.bf", temp).status_code == 200
    # Le mot de passe n'est ni stocké en clair ni journalisé
    assert temp not in str(
        db.scalar(select(User).where(User.email == "nouveau.delegue@exemple.bf")).password_hash
    )
    assert all(temp not in str(e.changes) for e in db.scalars(select(AuditLog)))

    dup = client.post(
        "/api/v1/admin/users",
        json={"email": "nouveau.delegue@exemple.bf", "full_name": "X Y", "role": "delegue_match"},
        headers=sa,
    )
    assert dup.status_code == 422 and dup.json()["code"] == "duplicate_email"


def test_club_manager_requires_team(client, db, seeded):
    sa = login(client, "superadmin@lds.local")
    r = client.post(
        "/api/v1/admin/users",
        json={
            "email": "club@exemple.bf",
            "full_name": "Club Sans Équipe",
            "role": "gestionnaire_club",
        },
        headers=sa,
    )
    assert r.status_code == 422
    team = db.scalar(select(Team).where(Team.short_name == "Soum FC"))
    r = client.post(
        "/api/v1/admin/users",
        json={
            "email": "club@exemple.bf",
            "full_name": "Gestion Soum",
            "role": "gestionnaire_club",
            "team_id": str(team.id),
        },
        headers=sa,
    )
    assert r.status_code == 201 and r.json()["user"]["team"]["name"] == "Soum FC"


def test_deactivate_and_reset_revoke_access(client, db, seeded):
    sa = login(client, "superadmin@lds.local")
    login(client, "technique@lds.local")
    refresh = client.cookies.get("lds_refresh")
    tech = db.scalar(select(User).where(User.email == "technique@lds.local"))

    r = client.patch(f"/api/v1/admin/users/{tech.id}", json={"is_active": False}, headers=sa)
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert _login_raw(client, "technique@lds.local", DEMO_PASSWORD).status_code == 401
    client.cookies.set("lds_refresh", refresh, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401

    client.patch(f"/api/v1/admin/users/{tech.id}", json={"is_active": True}, headers=sa)
    r = client.post(f"/api/v1/admin/users/{tech.id}/reset-password", headers=sa)
    temp = r.json()["temporary_password"]
    assert _login_raw(client, "technique@lds.local", DEMO_PASSWORD).status_code == 401
    assert _login_raw(client, "technique@lds.local", temp).status_code == 200


def test_last_super_admin_is_protected(client, db, seeded):
    sa = login(client, "superadmin@lds.local")
    me = db.scalar(select(User).where(User.email == "superadmin@lds.local"))
    r = client.patch(f"/api/v1/admin/users/{me.id}", json={"is_active": False}, headers=sa)
    assert r.status_code == 422
    r = client.patch(f"/api/v1/admin/users/{me.id}", json={"role": "admin_competition"}, headers=sa)
    assert r.status_code == 422


def test_change_own_password(client, seeded):
    headers = login(client, "controle@lds.local")
    bad = client.post(
        "/api/v1/auth/password",
        json={"current_password": "faux", "new_password": "Nouveau-mot-de-passe-2027"},
        headers=headers,
    )
    assert bad.status_code == 422 and bad.json()["code"] == "wrong_password"
    short = client.post(
        "/api/v1/auth/password",
        json={"current_password": DEMO_PASSWORD, "new_password": "court"},
        headers=headers,
    )
    assert short.status_code == 422 and short.json()["code"] == "weak_password"
    ok = client.post(
        "/api/v1/auth/password",
        json={"current_password": DEMO_PASSWORD, "new_password": "Nouveau-mot-de-passe-2027"},
        headers=headers,
    )
    assert ok.status_code == 204
    assert _login_raw(client, "controle@lds.local", "Nouveau-mot-de-passe-2027").status_code == 200


def test_assign_delegate(client, db, as_admin, seeded):
    pool = db.scalar(select(Pool).where(Pool.code == "B"))
    match = db.scalar(select(Match).where(Match.pool_id == pool.id).order_by(Match.round_number))
    delegates = client.get("/api/v1/admin/delegates", headers=as_admin).json()
    assert [d["email"] for d in delegates] == ["delegue@lds.local"]

    # Un compte qui n'est pas délégué est refusé
    club = db.scalar(select(User).where(User.email == "club.vinnim@lds.local"))
    r = client.put(
        f"/api/v1/admin/matches/{match.id}/delegate",
        json={"user_id": str(club.id)},
        headers=as_admin,
    )
    assert r.status_code == 422

    r = client.put(
        f"/api/v1/admin/matches/{match.id}/delegate",
        json={"user_id": delegates[0]["id"]},
        headers=as_admin,
    )
    assert r.status_code == 200 and r.json()["email"] == "delegue@lds.local"
    assignments = client.get("/api/v1/admin/delegate-assignments", headers=as_admin).json()
    assert assignments[str(match.id)]["email"] == "delegue@lds.local"

    # Un autre délégué ne voit plus ce match dans sa liste
    sa = login(client, "superadmin@lds.local")
    other = client.post(
        "/api/v1/admin/users",
        json={
            "email": "autre.delegue@exemple.bf",
            "full_name": "Autre Délégué",
            "role": "delegue_match",
        },
        headers=sa,
    ).json()
    r = _login_raw(client, "autre.delegue@exemple.bf", other["temporary_password"])
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    client.post(
        "/api/v1/auth/password",
        json={
            "current_password": other["temporary_password"],
            "new_password": "Autre-delegue-2027",
        },
        headers=headers,
    )
    listed = client.get("/api/v1/delegate/matches", params={"all": True}, headers=headers).json()
    assert str(match.id) not in {m["id"] for m in listed}
    assert client.get(f"/api/v1/matches/{match.id}/sheet", headers=headers).status_code == 403

    # Retrait de l'attribution
    r = client.put(
        f"/api/v1/admin/matches/{match.id}/delegate", json={"user_id": None}, headers=as_admin
    )
    assert r.status_code == 200 and r.json() is None


def test_assignment_forbidden_for_club(client, db, as_club, seeded):
    match = db.scalar(select(Match).where(Match.round_number == 1))
    r = client.put(
        f"/api/v1/admin/matches/{match.id}/delegate", json={"user_id": None}, headers=as_club
    )
    assert r.status_code == 403


def test_temporary_password_must_be_changed_first(client, db, seeded):
    sa = login(client, "superadmin@lds.local")
    created = client.post(
        "/api/v1/admin/users",
        json={
            "email": "premier@exemple.bf",
            "full_name": "Première Connexion",
            "role": "delegue_match",
        },
        headers=sa,
    ).json()
    assert created["user"]["must_change_password"] is True
    temp = created["temporary_password"]
    r = _login_raw(client, "premier@exemple.bf", temp)
    assert r.status_code == 200 and r.json()["user"]["must_change_password"] is True
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # Tout est bloqué sauf « Mon compte »
    blocked = client.get("/api/v1/delegate/matches", headers=headers)
    assert blocked.status_code == 403 and "provisoire" in blocked.json()["detail"]
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    ok = client.post(
        "/api/v1/auth/password",
        json={"current_password": temp, "new_password": "Mon-vrai-mot-de-passe"},
        headers=headers,
    )
    assert ok.status_code == 204
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["must_change_password"] is False
    assert client.get("/api/v1/delegate/matches", headers=headers).status_code == 200

    # Une réinitialisation par l'administration réimpose le changement
    user_id = created["user"]["id"]
    client.post(f"/api/v1/admin/users/{user_id}/reset-password", headers=sa)
    assert client.get("/api/v1/delegate/matches", headers=headers).status_code == 403


def test_demo_and_cli_accounts_are_not_blocked(client, as_delegate):
    assert client.get("/api/v1/delegate/matches", headers=as_delegate).status_code == 200
