"""Identité visuelle : logo de la Ligue et logos des équipes (envoi, contrôles, diffusion)."""

import pytest
from sqlalchemy import select

from lds_api.models import AuditLog, Team
from lds_api.providers.storage import LocalStorage
from lds_api.services import media

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


@pytest.fixture(autouse=True)
def storage(monkeypatch, tmp_path):
    s = LocalStorage(str(tmp_path))
    monkeypatch.setattr(media, "get_storage", lambda: s)
    return s


def upload(client, url, data, headers, name="logo.png"):
    return client.put(
        url, files={"file": (name, data, "application/octet-stream")}, headers=headers
    )


def test_brand_logo_lifecycle(client, db, as_admin, seeded):
    from .conftest import login

    superadmin = login(client, "superadmin@lds.local")
    assert client.get("/api/v1/brand").json() == {"logo_url": None}
    # Réservé au Secrétariat exécutif (super administrateur)
    assert upload(client, "/api/v1/admin/brand/logo", PNG, as_admin).status_code == 403

    r = upload(client, "/api/v1/admin/brand/logo", PNG, superadmin)
    assert r.status_code == 200, r.text
    url = r.json()["logo_url"]
    assert url.startswith("/api/v1/media/brand/logo-") and url.endswith(".png")
    assert client.get("/api/v1/brand").json()["logo_url"] == url
    img = client.get(url)
    assert img.status_code == 200 and img.content == PNG
    assert (
        img.headers["content-type"] == "image/png" and "immutable" in img.headers["cache-control"]
    )

    # Nouveau logo : nouvelle adresse, l'ancienne disparaît
    url2 = upload(client, "/api/v1/admin/brand/logo", JPG, superadmin).json()["logo_url"]
    assert url2 != url and url2.endswith(".jpg") and client.get(url).status_code == 404

    assert client.delete("/api/v1/admin/brand/logo", headers=superadmin).status_code == 204
    assert client.get("/api/v1/brand").json() == {"logo_url": None}
    assert db.scalars(select(AuditLog).where(AuditLog.entity_type == "brand")).all()


def test_rejects_svg_and_large_files(client, seeded):
    from .conftest import login

    superadmin = login(client, "superadmin@lds.local")
    r = upload(client, "/api/v1/admin/brand/logo", SVG, superadmin, name="logo.png")
    assert r.status_code == 422 and r.json()["code"] == "image_format"
    big = PNG + b"\x00" * media.MAX_BYTES
    r = upload(client, "/api/v1/admin/brand/logo", big, superadmin)
    assert r.status_code == 422 and r.json()["code"] == "image_too_large"


def test_team_logo_shown_on_public_pages(client, db, as_admin, as_club):
    team = db.scalar(select(Team).where(Team.short_name == "Vinnim"))
    url = f"/api/v1/admin/teams/{team.id}/logo"
    assert upload(client, url, PNG, as_club).status_code == 403
    r = upload(client, url, PNG, as_admin)
    assert r.status_code == 200, r.text
    logo = r.json()["logo_url"]
    assert logo.startswith(f"/api/v1/media/teams/{team.id}/logo-")

    assert client.get(f"/api/v1/teams/{team.slug}").json()["logo_url"] == logo
    match = next(m for m in client.get("/api/v1/matches").json() if m["home"]["id"] == str(team.id))
    assert match["home"]["logo_url"] == logo
    assert client.get(logo).content == PNG

    r = client.delete(url, headers=as_admin)
    assert r.status_code == 200 and r.json()["logo_url"] is None
    assert client.get(logo).status_code == 404


def test_only_logo_keys_are_public(client, storage):
    storage.put("persons/abc/photo.png", PNG, "image/png")
    assert client.get("/api/v1/media/persons/abc/photo.png").status_code == 404
    assert client.get("/api/v1/media/../secret").status_code == 404
