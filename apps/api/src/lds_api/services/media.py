"""Images de la plateforme : logo de la Ligue et logos des équipes (publics), photos des
licences (privées).

Les fichiers sont dans le stockage de la plateforme (disque ou S3), jamais dans le dépôt de
code. Chaque version a un nom unique (empreinte du contenu) : on peut la mettre en cache
indéfiniment, et changer de logo change l'adresse. Seuls PNG, JPEG et WebP sont acceptés,
reconnus à leurs premiers octets (le SVG est refusé : il peut contenir du script).
"""

import hashlib
import re
import uuid
from datetime import date

from sqlalchemy.orm import Session

from lds_api.core.errors import BusinessError, NotFound
from lds_api.domain.eligibility import age_on
from lds_api.models import Person, Team
from lds_api.providers.storage import get_storage
from lds_api.services import audit

MAX_BYTES = 1_000_000
BRAND_POINTER = "brand/current"
# Seules ces clés sont servies publiquement (jamais les photos ou documents des personnes)
PUBLIC_KEY = re.compile(r"^(brand/logo|teams/[0-9a-f-]{36}/logo)-[0-9a-f]{12}\.(png|jpg|webp)$")
# Photos des personnes : clés distinctes, servies seulement aux comptes habilités
PERSON_PHOTO = re.compile(r"^persons/[0-9a-f-]{36}/photo-[0-9a-f]{12}\.(png|jpg|webp)$")
TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


def sniff(data: bytes) -> str:
    """Extension déduite du contenu (et non du nom de fichier envoyé)."""
    if len(data) > MAX_BYTES:
        raise BusinessError("Image trop lourde (1 Mo au maximum)", code="image_too_large")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    raise BusinessError("Format non accepté : PNG, JPEG ou WebP", code="image_format")


def _store(prefix: str, data: bytes) -> str:
    ext = sniff(data)
    key = f"{prefix}-{hashlib.sha256(data).hexdigest()[:12]}.{ext}"
    get_storage().put(key, data, TYPES[ext])
    return key


def public_url(key: str | None) -> str | None:
    return f"/api/v1/media/{key}" if key else None


def read_public(key: str) -> tuple[bytes, str]:
    if not PUBLIC_KEY.match(key):
        raise NotFound("Fichier introuvable")
    try:
        data = get_storage().get(key)
    except (FileNotFoundError, KeyError, OSError) as exc:
        raise NotFound("Fichier introuvable") from exc
    return data, TYPES[key.rsplit(".", 1)[1]]


# --- Logo de la Ligue -----------------------------------------------------------------------
def brand_key() -> str | None:
    try:
        key = get_storage().get(BRAND_POINTER).decode().strip()
    except Exception:  # noqa: BLE001 — fichier absent (disque ou S3) : marque provisoire
        return None
    return key if PUBLIC_KEY.match(key) else None


def set_brand_logo(db: Session, actor, data: bytes) -> str:
    old = brand_key()
    key = _store("brand/logo", data)
    get_storage().put(BRAND_POINTER, key.encode(), "text/plain")
    if old and old != key:
        get_storage().delete(old)
    audit.record(db, actor, "update", "brand", None, {"logo": key})
    return key


def delete_brand_logo(db: Session, actor) -> None:
    old = brand_key()
    if old:
        get_storage().delete(old)
    get_storage().delete(BRAND_POINTER)
    audit.record(db, actor, "delete", "brand", None, {"logo": old})


# --- Logos des équipes ----------------------------------------------------------------------
def set_team_logo(db: Session, actor, team_id: uuid.UUID, data: bytes) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise NotFound("Équipe introuvable")
    old = team.logo_path
    team.logo_path = _store(f"teams/{team.id}/logo", data)
    if old and old != team.logo_path and PUBLIC_KEY.match(old):
        get_storage().delete(old)
    audit.record(db, actor, "update_logo", "team", team.id, {"logo": [old, team.logo_path]})
    return team


def delete_team_logo(db: Session, actor, team_id: uuid.UUID) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise NotFound("Équipe introuvable")
    if team.logo_path and PUBLIC_KEY.match(team.logo_path):
        get_storage().delete(team.logo_path)
    audit.record(db, actor, "delete_logo", "team", team.id, {"logo": team.logo_path})
    team.logo_path = None
    return team


# --- Photos d'identité (licences) : privées, jamais servies par /media ----------------------
def _is_minor_today(person: Person) -> bool:
    return age_on(person.birth_date, date.today()) < 18


def _private_photo(person: Person) -> str | None:
    key = person.photo_path
    return key if key and PERSON_PHOTO.match(key) else None


def set_person_photo(db: Session, actor, person: Person, data: bytes) -> Person:
    """Photo de licence. Pour un mineur, l'autorisation parentale doit être enregistrée."""
    if _is_minor_today(person) and person.guardian_consent_on is None:
        raise BusinessError(
            "Joueur mineur : enregistrez d'abord la date de l'autorisation parentale",
            code="guardian_consent_required",
        )
    old = _private_photo(person)
    person.photo_path = _store(f"persons/{person.id}/photo", data)
    if old and old != person.photo_path:
        get_storage().delete(old)
    audit.record(
        db, actor, "update_photo", "person", person.id, {"photo": "remplacée" if old else "ajoutée"}
    )
    return person


def delete_person_photo(db: Session, actor, person: Person) -> None:
    old = _private_photo(person)
    if old:
        get_storage().delete(old)
    person.photo_path = None
    audit.record(db, actor, "delete_photo", "person", person.id, None)


def read_person_photo(person: Person) -> tuple[bytes, str]:
    key = _private_photo(person)
    if key is None:
        raise NotFound("Aucune photo")
    try:
        data = get_storage().get(key)
    except (FileNotFoundError, KeyError, OSError) as exc:
        raise NotFound("Aucune photo") from exc
    return data, TYPES[key.rsplit(".", 1)[1]]


# --- Import en lot des blasons (archive ZIP) ------------------------------------------------
def _norm(text: str) -> str:
    import unicodedata

    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    plain = re.sub(r"^\d+[_\- ]*", "", plain)  # numéro d'ordre en tête de fichier
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def match_team(filename: str, teams: list[Team]) -> tuple[Team | None, float]:
    """Équipe correspondant au nom de fichier (« 05_Union_Sportive_des_Koulse_USK.png »)."""
    from difflib import SequenceMatcher

    stem = _norm(filename.rsplit("/", 1)[-1].rsplit(".", 1)[0])
    best, score = None, 0.0
    for t in teams:
        names = [t.name, t.short_name, t.slug.replace("-", " ")] + (
            [t.acronym] if t.acronym else []
        )
        s = max(SequenceMatcher(None, stem, _norm(n)).ratio() for n in names)
        # Nom complet contenu dans le fichier (le fichier ajoute souvent le sigle)
        if _norm(t.name) and _norm(t.name) in stem:
            s = max(s, 0.95)
        if s > score:
            best, score = t, s
    return best, score


def import_team_logos(db: Session, actor, archive: bytes, *, dry_run: bool = False) -> list[dict]:
    """Associe chaque image de l'archive à une équipe et l'enregistre comme son blason.

    Seules les correspondances sûres (score ≥ 0,75, une image par équipe) sont appliquées ;
    les autres sont signalées pour un envoi manuel depuis le back-office.
    """
    import io
    import zipfile

    from sqlalchemy import select

    teams = list(db.scalars(select(Team)))
    report: list[dict] = []
    used: set = set()
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        names = sorted(
            n
            for n in zf.namelist()
            if not n.endswith("/")
            and n.lower().rsplit(".", 1)[-1] in {"png", "jpg", "jpeg", "webp"}
            and not n.rsplit("/", 1)[-1].lower().startswith(("apercu", "aperçu", "preview", "."))
        )
        for name in names:
            team, score = match_team(name, teams)
            entry = {"file": name, "team": team.name if team else None, "score": round(score, 2)}
            if team is None or score < 0.75:
                entry["status"] = "sans correspondance sûre"
            elif team.id in used:
                entry["status"] = "équipe déjà servie par un autre fichier"
            else:
                used.add(team.id)
                if not dry_run:
                    set_team_logo(db, actor, team.id, zf.read(name))
                entry["status"] = "à importer" if dry_run else "importé"
            report.append(entry)
    return report
