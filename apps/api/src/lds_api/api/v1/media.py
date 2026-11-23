"""Identité visuelle : logo de la Ligue, logos des équipes (envoi et diffusion publique)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, UploadFile, status
from pydantic import BaseModel

from lds_api.core.deps import Actor, DbSession, require
from lds_api.core.rbac import Perm
from lds_api.schemas.fixtures import TeamRef
from lds_api.services import media

router = APIRouter(tags=["identité visuelle"])
BrandManager = Annotated[Actor, Depends(require(Perm.BRAND_MANAGE))]
TeamManager = Annotated[Actor, Depends(require(Perm.TEAM_MANAGE))]


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
