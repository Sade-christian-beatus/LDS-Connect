"""Double authentification TOTP (M9)."""

import time

import pytest
from sqlalchemy import select

from lds_api.core.config import get_settings
from lds_api.domain import totp
from lds_api.models import AuditLog, User

from .conftest import login

PASSWORD = "Lds2027-demo"


def _code(secret: str, offset: int = 0) -> str:
    return totp.code_at(secret, totp.step_for(time.time()) + offset)


def _enable(client, headers) -> str:
    setup = client.post("/api/v1/auth/mfa/setup", headers=headers).json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/") and "<svg" in setup["qr_svg"]
    r = client.post("/api/v1/auth/mfa/enable", json={"code": "000000"}, headers=headers)
    assert r.status_code == 422
    r = client.post(
        "/api/v1/auth/mfa/enable", json={"code": _code(setup["secret"])}, headers=headers
    )
    assert r.status_code == 200 and r.json()["mfa_enabled"] is True
    return setup["secret"]


def test_enable_then_two_step_login(client, db, seeded):
    headers = login(client, "delegue@lds.local")
    secret = _enable(client, headers)

    r = client.post("/api/v1/auth/login", json={"email": "delegue@lds.local", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["mfa_required"] is True and "access_token" not in body
    token = body["mfa_token"]

    bad = client.post("/api/v1/auth/login/mfa", json={"mfa_token": token, "code": "123456"})
    assert bad.status_code == 401
    # Le code de l'activation a déjà servi : on prend le pas suivant
    code = _code(secret, 1)
    ok = client.post("/api/v1/auth/login/mfa", json={"mfa_token": token, "code": code})
    assert ok.status_code == 200, ok.text
    assert ok.json()["user"]["mfa_enabled"] is True
    # Un code ne sert qu'une fois
    again = client.post("/api/v1/auth/login/mfa", json={"mfa_token": token, "code": code})
    assert again.status_code == 401
    # Un jeton d'accès ne remplace pas le jeton intermédiaire (et inversement)
    access = ok.json()["access_token"]
    r = client.post("/api/v1/auth/login/mfa", json={"mfa_token": access, "code": _code(secret)})
    assert r.status_code == 401
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401

    actions = set(db.scalars(select(AuditLog.action).where(AuditLog.entity_type == "user")))
    assert {"mfa_enable", "mfa_failed"} <= actions


def test_required_for_admin_roles(client, db, seeded, monkeypatch):
    monkeypatch.setattr(get_settings(), "mfa_required_roles", "super_admin,admin_competition")
    headers = login(client, "admin@lds.local")
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["mfa_setup_required"] is True
    r = client.get("/api/v1/admin/teams/overview", headers=headers)
    assert r.status_code == 403 and r.headers["x-lds-reason"] == "mfa_setup_required"
    secret = _enable(client, headers)
    assert client.get("/api/v1/admin/teams/overview", headers=headers).status_code == 200
    # Obligatoire pour ce rôle : pas de désactivation
    r = client.post("/api/v1/auth/mfa/disable", json={"code": _code(secret, 1)}, headers=headers)
    assert r.status_code == 422
    # Les autres rôles n'y sont pas tenus
    club = login(client, "club.vinnim@lds.local")
    assert client.get("/api/v1/auth/me", headers=club).json()["mfa_setup_required"] is False


def test_superadmin_resets_lost_phone(client, db, seeded):
    headers = login(client, "delegue@lds.local")
    _enable(client, headers)
    user = db.scalar(select(User).where(User.email == "delegue@lds.local"))
    superadmin = login(client, "superadmin@lds.local")
    users = client.get("/api/v1/admin/users", headers=superadmin).json()
    assert next(u for u in users if u["email"] == "delegue@lds.local")["mfa_enabled"] is True
    r = client.post(f"/api/v1/admin/users/{user.id}/reset-mfa", headers=superadmin)
    assert r.status_code == 200 and r.json()["mfa_enabled"] is False
    body = client.post(
        "/api/v1/auth/login", json={"email": "delegue@lds.local", "password": PASSWORD}
    ).json()
    assert "access_token" in body


@pytest.mark.parametrize(
    "roles,expected", [(None, set()), ("", set()), ("super_admin", {"super_admin"})]
)
def test_mfa_roles_setting(monkeypatch, roles, expected):
    monkeypatch.setattr(get_settings(), "mfa_required_roles", roles)
    assert get_settings().mfa_roles == expected
