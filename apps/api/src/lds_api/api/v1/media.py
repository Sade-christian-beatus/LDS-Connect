"""Images : logo de la Ligue, logos des équipes (publics), photos des licences (privées)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select

from lds_api.core.deps import Actor, DbSession, ensure_team_scope, require
from lds_api.core.errors import NotFound
from lds_api.core.rbac import Perm
from lds_api.models import Licence, Person
from lds_api.schemas.fixtures import TeamRef
from lds_api.services import media, registry

router = APIRouter(tags=["identité visuelle"])
BrandManager = Annotated[Actor, Depends(require(Perm.BRAND_MANAGE))]
TeamManager = Annotated[Actor, Depends(require(Perm.TEAM_MANAGE))]
SquadReader = Annotated[Actor, Depends(require(Perm.SQUAD_READ))]
SquadWriter = Annotated[Actor, Depends(require(Perm.SQUAD_WRITE))]
Verifier = Annotated[Actor, Depends(require(Perm.LICENCE_VERIFY))]


class BrandOut(BaseModel):
    logo_url: str | None  # None : marque provisoire (aucun logo envoyé)


async def _read(file: UploadFile) -> bytes:
    data = await file.read(media.MAX_BYTES + 1)
    return data


@router.get("/brand", response_model=BrandOut)
def brand(response: Response):
    response.headers["Cache-Control"] = "public, max-age=60"
    return BrandOut(logo_url=media.public_url(media.brand_key()))


@router.get(
    "/media/{key:path}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}}}},
)
def public_media(key: str):
    data, content_type = media.read_public(key)
    # Nom unique par version : cache illimité côté navigateur et service worker
    return Response(
        data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.put("/admin/brand/logo", response_model=BrandOut)
async def upload_brand_logo(file: UploadFile, db: DbSession, actor: BrandManager):
    key = media.set_brand_logo(db, actor, await _read(file))
    db.commit()
    return BrandOut(logo_url=media.public_url(key))


@router.delete("/admin/brand/logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand_logo(db: DbSession, actor: BrandManager):
    media.delete_brand_logo(db, actor)
    db.commit()


@router.put("/admin/teams/{team_id}/logo", response_model=TeamRef)
async def upload_team_logo(team_id: uuid.UUID, file: UploadFile, db: DbSession, actor: TeamManager):
    team = media.set_team_logo(db, actor, team_id, await _read(file))
    db.commit()
    return TeamRef.model_validate(team)


@router.delete("/admin/teams/{team_id}/logo", response_model=TeamRef)
def delete_team_logo(team_id: uuid.UUID, db: DbSession, actor: TeamManager):
    team = media.delete_team_logo(db, actor, team_id)
    db.commit()
    return TeamRef.model_validate(team)


# --- Photos de licence (privées) ------------------------------------------------------------
PRIVATE_IMAGE = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
IMAGE_RESPONSES = {200: {"content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}}}}


def _scoped_person(db, actor: Actor, person_id: uuid.UUID) -> Person:
    m = registry.membership_for(db, person_id)
    ensure_team_scope(actor, m.team_id)
    return m.person


@router.put("/admin/persons/{person_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
async def upload_person_photo(
    person_id: uuid.UUID, file: UploadFile, db: DbSession, actor: SquadWriter
):
    data = await _read(file)
    media.set_person_photo(db, actor, _scoped_person(db, actor, person_id), data)
    db.commit()


@router.delete("/admin/persons/{person_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def delete_person_photo(person_id: uuid.UUID, db: DbSession, actor: SquadWriter):
    media.delete_person_photo(db, actor, _scoped_person(db, actor, person_id))
    db.commit()


@router.get("/admin/persons/{person_id}/photo", response_class=Response, responses=IMAGE_RESPONSES)
def person_photo(person_id: uuid.UUID, db: DbSession, actor: SquadReader):
    data, content_type = media.read_person_photo(_scoped_person(db, actor, person_id))
    return Response(data, media_type=content_type, headers=PRIVATE_IMAGE)


@router.get("/licences/{number}/photo", response_class=Response, responses=IMAGE_RESPONSES)
def licence_photo(number: str, db: DbSession, actor: Verifier):
    """Photo du titulaire, pour le contrôleur au stade (comparaison avec la personne)."""
    lic = db.scalar(select(Licence).where(Licence.number == number))
    if lic is None:
        raise NotFound("Licence")
    data, content_type = media.read_person_photo(lic.membership.person)
    return Response(data, media_type=content_type, headers=PRIVATE_IMAGE)
