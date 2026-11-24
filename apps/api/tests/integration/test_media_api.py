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


# --- Photos de licence ----------------------------------------------------------------------
def _vinnim_players(db):
    from datetime import date

    from lds_api.domain.eligibility import age_on
    from lds_api.models import Licence, SquadMembership

    team = db.scalar(select(Team).where(Team.short_name == "Vinnim"))
    rows = db.scalars(
        select(SquadMembership).where(
            SquadMembership.team_id == team.id, SquadMembership.licence.has()
        )
    ).all()
    adult = next(m for m in rows if age_on(m.person.birth_date, date.today()) >= 18)
    minor = next((m for m in rows if age_on(m.person.birth_date, date.today()) < 18), None)
    number = db.scalar(select(Licence.number).where(Licence.membership_id == adult.id))
    return team, adult.person, minor.person if minor else None, number


def test_licence_photo_is_private(client, db, as_club, as_controller, storage):
    team, adult, _, number = _vinnim_players(db)
    url = f"/api/v1/admin/persons/{adult.id}/photo"
    assert client.get(url, headers=as_club).status_code == 404
    assert upload(client, url, SVG, as_club, "photo.svg").status_code == 422
    r = upload(client, url, JPG, as_club, "photo.jpg")
    assert r.status_code == 204, r.text

    db.expire_all()
    key = db.get(type(adult), adult.id).photo_path
    assert key.startswith(f"persons/{adult.id}/photo-") and key.endswith(".jpg")
    # Jamais servie publiquement, même avec la bonne clé
    assert client.get(f"/api/v1/media/{key}").status_code == 404

    r = client.get(url, headers=as_club)
    assert r.status_code == 200 and r.content == JPG
    assert r.headers["content-type"] == "image/jpeg" and "no-store" in r.headers["cache-control"]
    # Le contrôleur au stade la voit par le numéro de licence, pas sans compte
    assert client.get(f"/api/v1/licences/{number}/photo", headers=as_controller).content == JPG
    assert client.get(f"/api/v1/licences/{number}/photo").status_code == 401
    squad = client.get(f"/api/v1/admin/teams/{team.id}/squad", headers=as_club).json()
    assert next(m for m in squad["members"] if m["person_id"] == str(adult.id))["has_photo"]

    assert client.delete(url, headers=as_club).status_code == 204
    assert client.get(url, headers=as_club).status_code == 404
    assert not list(storage.root.rglob("photo-*"))
    actions = db.scalars(select(AuditLog.action).where(AuditLog.entity_id == str(adult.id))).all()
    assert {"update_photo", "delete_photo"} <= set(actions)


def test_minor_photo_requires_guardian_consent(client, db, as_club):
    from datetime import date

    _, _, minor, _ = _vinnim_players(db)
    if minor is None:
        pytest.skip("aucun mineur licencié dans le seed")
    minor.guardian_consent_on = None
    db.commit()
    url = f"/api/v1/admin/persons/{minor.id}/photo"
    r = upload(client, url, PNG, as_club)
    assert r.status_code == 422 and r.json()["code"] == "guardian_consent_required"
    minor.guardian_consent_on = date.today()
    db.commit()
    assert upload(client, url, PNG, as_club).status_code == 204
