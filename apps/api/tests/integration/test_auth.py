from sqlalchemy import select

from lds_api.models import AuditLog

from .conftest import DEMO_PASSWORD, login


def test_login_success_returns_token_and_cookie(client, seeded):
    r = client.post(
        "/api/v1/auth/login", json={"email": "admin@lds.local", "password": DEMO_PASSWORD}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["roles"] == ["admin_competition"]
    assert "lds_refresh" in r.cookies
    assert "httponly" in r.headers["set-cookie"].lower()


def test_login_wrong_password(client, seeded):
    r = client.post("/api/v1/auth/login", json={"email": "admin@lds.local", "password": "faux"})
    assert r.status_code == 401
    assert "incorrect" in r.json()["detail"]


def test_login_unknown_email_same_message(client, seeded):
    r = client.post("/api/v1/auth/login", json={"email": "x@lds.local", "password": "faux"})
    assert r.status_code == 401
    assert "incorrect" in r.json()["detail"]


def test_login_rate_limited(client, seeded):
    for _ in range(10):
        client.post("/api/v1/auth/login", json={"email": "admin@lds.local", "password": "x"})
    r = client.post("/api/v1/auth/login", json={"email": "admin@lds.local", "password": "x"})
    assert r.status_code == 429


def test_me_requires_token(client, seeded):
    assert client.get("/api/v1/auth/me").status_code == 401
    bad = {"Authorization": "Bearer pas-un-jeton"}
    assert client.get("/api/v1/auth/me", headers=bad).status_code == 401


def test_me_returns_permissions(client, as_club):
    me = client.get("/api/v1/auth/me", headers=as_club).json()
    assert me["roles"] == ["gestionnaire_club"]
    assert "squad:write" in me["permissions"]
    assert "licence:issue" not in me["permissions"]
    assert me["team_id"]


def test_refresh_rotation_and_reuse_detection(client, seeded):
    login(client, "admin@lds.local")
    first = client.cookies.get("lds_refresh")
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    second = client.cookies.get("lds_refresh")
    assert second and second != first

    # Rejouer l'ancien jeton : refusé, et toute la famille est révoquée
    client.cookies.set("lds_refresh", first, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401
    client.cookies.set("lds_refresh", second, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_refresh(client, seeded):
    login(client, "admin@lds.local")
    token = client.cookies.get("lds_refresh")
    assert client.post("/api/v1/auth/logout").status_code == 204
    client.cookies.set("lds_refresh", token, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_login_is_audited(client, db, seeded):
    login(client, "delegue@lds.local")
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "login"))
    assert entry is not None and "delegue@lds.local" in entry.actor_label
