"""Feuille de match numérique (délégué) et liste des matchs à traiter."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select

from lds_api.core.deps import Actor, DbSession, require
from lds_api.core.rbac import Perm
from lds_api.models import Match, MatchSheet
from lds_api.schemas import matchsheet as ms
from lds_api.services import fixtures, seasons
from lds_api.services import matchsheet as svc

router = APIRouter(tags=["feuille de match"])

Editor = Annotated[Actor, Depends(require(Perm.SHEET_EDIT))]
Validator = Annotated[Actor, Depends(require(Perm.SHEET_VALIDATE))]
Closer = Annotated[Actor, Depends(require(Perm.SHEET_CLOSE))]


@router.get("/delegate/matches", response_model=list[ms.DelegateMatch])
def delegate_matches(
    db: DbSession,
    actor: Editor,
    days: Annotated[int, Query(ge=1, le=365, description="Fenêtre en jours")] = 30,
    all_: Annotated[bool, Query(alias="all")] = False,
):
    """Matchs à traiter : en cours, et ceux des `days` prochains jours (ou tous)."""
    season = seasons.current_season(db)
    q = fixtures.match_query().where(
        Match.season_id == season.id,
        Match.home_team_id.is_not(None),
        Match.away_team_id.is_not(None),
    )
    if not all_:
        now = datetime.now(UTC)
        q = q.where((Match.kickoff_at.is_(None)) | (Match.kickoff_at <= now + timedelta(days=days)))
    matches = list(db.scalars(q.order_by(Match.kickoff_at.nulls_last(), Match.round_number)))
    sheets = {
        s.match_id: s
        for s in db.scalars(
            select(MatchSheet).where(MatchSheet.match_id.in_([m.id for m in matches]))
        )
    }
    out = []
    for m in matches:
        sheet = sheets.get(m.id)
        assigned_elsewhere = (
            sheet is not None
            and sheet.delegate_user_id is not None
            and sheet.delegate_user_id != actor.id
        )
        if assigned_elsewhere and not actor.can(Perm.SHEET_CLOSE):
            continue
        out.append(
            ms.DelegateMatch(
                **fixtures.to_out(m).model_dump(), sheet_status=sheet.status if sheet else None
            )
        )
    return out


@router.get("/matches/{match_id}/sheet", response_model=ms.SheetOut)
def get_sheet(match_id: uuid.UUID, db: DbSession, actor: Editor):
    """Ouvre (et crée au besoin) la feuille de match."""
    sheet = svc.get_sheet(db, match_id, create=True)
    svc.ensure_can_edit(actor, sheet)
    db.commit()
    return svc.view(db, sheet)


@router.put("/matches/{match_id}/sheet/lineup/{team_id}", response_model=ms.SheetOut)
def put_lineup(
    match_id: uuid.UUID, team_id: uuid.UUID, body: ms.LineupIn, db: DbSession, actor: Editor
):
    sheet = svc.get_sheet(db, match_id, create=True)
    svc.ensure_can_edit(actor, sheet)
    svc.set_lineup(db, actor, sheet, team_id, body)
    db.commit()
    return svc.view(db, sheet)


@router.patch("/matches/{match_id}/sheet", response_model=ms.SheetOut)
def patch_header(match_id: uuid.UUID, body: ms.SheetHeaderIn, db: DbSession, actor: Editor):
    sheet = svc.get_sheet(db, match_id, create=True)
    svc.ensure_can_edit(actor, sheet)
    svc.update_header(db, actor, sheet, body)
    db.commit()
    return svc.view(db, sheet)


@router.post("/matches/{match_id}/sheet/submit", response_model=ms.SheetOut)
def submit(match_id: uuid.UUID, db: DbSession, actor: Editor):
    sheet = svc.get_sheet(db, match_id)
    svc.ensure_can_edit(actor, sheet)
    svc.submit(db, actor, sheet)
    db.commit()
    return svc.view(db, sheet)


@router.post("/matches/{match_id}/sheet/reopen", response_model=ms.SheetOut)
def reopen(match_id: uuid.UUID, db: DbSession, actor: Editor):
    sheet = svc.get_sheet(db, match_id)
    svc.ensure_can_edit(actor, sheet)
    svc.reopen(db, actor, sheet)
    db.commit()
    return svc.view(db, sheet)


@router.post(
    "/matches/{match_id}/sheet/events",
    response_model=ms.SheetOut,
    status_code=status.HTTP_201_CREATED,
)
def add_event(match_id: uuid.UUID, body: ms.EventIn, db: DbSession, actor: Editor):
    sheet = svc.get_sheet(db, match_id)
    svc.ensure_can_edit(actor, sheet)
    svc.add_event(db, actor, sheet, body)
    db.commit()
    return svc.view(db, sheet)


@router.delete("/matches/{match_id}/sheet/events/{event_id}", response_model=ms.SheetOut)
def delete_event(match_id: uuid.UUID, event_id: uuid.UUID, db: DbSession, actor: Editor):
    sheet = svc.get_sheet(db, match_id)
    svc.ensure_can_edit(actor, sheet)
    svc.delete_event(db, actor, sheet, event_id)
    db.commit()
    return svc.view(db, sheet)


@router.post("/matches/{match_id}/sheet/validate", response_model=ms.SheetOut)
def validate(match_id: uuid.UUID, db: DbSession, actor: Validator):
    sheet = svc.get_sheet(db, match_id)
    svc.ensure_can_edit(actor, sheet)
    svc.validate(db, actor, sheet)
    db.commit()
    return svc.view(db, sheet)


@router.post("/matches/{match_id}/sheet/close", response_model=ms.SheetOut)
def close(match_id: uuid.UUID, db: DbSession, actor: Closer):
    sheet = svc.get_sheet(db, match_id)
    svc.close(db, actor, sheet)
    db.commit()
    return svc.view(db, sheet)
