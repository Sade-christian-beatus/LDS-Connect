"""Saisons, règles de la compétition et stades (administration de la Ligue)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from lds_api.core.deps import Actor, DbSession, require
from lds_api.core.rbac import Perm
from lds_api.schemas import seasons as s
from lds_api.schemas.fixtures import VenueOut
from lds_api.services import season_admin as svc
from lds_api.services import seasons

router = APIRouter(prefix="/admin", tags=["saisons et règles"])
RulesManager = Annotated[Actor, Depends(require(Perm.RULES_MANAGE))]
FixtureManager = Annotated[Actor, Depends(require(Perm.FIXTURE_MANAGE))]


@router.get("/rules", response_model=s.RulesAdminOut)
def current_rules(db: DbSession, actor: FixtureManager):
    return svc.rules_out(db, seasons.current_season(db))


@router.patch("/rules", response_model=s.RulesAdminOut)
def update_rules(body: s.RulesUpdate, db: DbSession, actor: RulesManager):
    out = svc.update_rules(db, actor, seasons.current_season(db), body)
    db.commit()
    return out


@router.get("/seasons", response_model=list[s.SeasonAdminOut])
def list_seasons(db: DbSession, actor: RulesManager):
    return svc.list_seasons(db)


@router.post("/seasons", response_model=s.SeasonAdminOut, status_code=status.HTTP_201_CREATED)
def create_season(body: s.SeasonCreate, db: DbSession, actor: RulesManager):
    season = svc.create_season(db, actor, body)
    db.commit()
    return next(x for x in svc.list_seasons(db) if x.id == season.id)


@router.post("/seasons/{season_id}/activate", response_model=s.SeasonAdminOut)
def activate_season(season_id: uuid.UUID, db: DbSession, actor: RulesManager):
    svc.activate_season(db, actor, season_id)
    db.commit()
    return next(x for x in svc.list_seasons(db) if x.id == season_id)


@router.patch("/venues/{venue_id}", response_model=VenueOut)
def update_venue(venue_id: uuid.UUID, body: s.VenueUpdate, db: DbSession, actor: FixtureManager):
    v = svc.update_venue(db, actor, venue_id, body)
    db.commit()
    return v
