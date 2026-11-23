"""Talents : page publique d'un joueur ; tableau de bord, fiche, suivi et notes (interne)."""

import csv
import io
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from lds_api.core.deps import Actor, DbSession, require
from lds_api.core.rbac import Perm
from lds_api.schemas import talents as ts
from lds_api.services import audit
from lds_api.services import talents as svc

router = APIRouter(tags=["talents"])
StatsReader = Annotated[Actor, Depends(require(Perm.STATS_READ))]
Scout = Annotated[Actor, Depends(require(Perm.TALENT_NOTES))]
Filters = Annotated[ts.DashboardFilters, Query()]


@router.get("/players/{person_id}", response_model=ts.PublicPlayerProfile)
def public_player(person_id: uuid.UUID, db: DbSession):
    """Fiche publique : nom d'usage, poste, équipe, âge et statistiques de la saison."""
    return svc.public_player(db, person_id)


@router.get("/admin/talents", response_model=ts.Dashboard)
def dashboard(filters: Filters, db: DbSession, actor: StatsReader):
    return svc.dashboard(db, filters)


@router.get(
    "/admin/talents.csv", response_class=Response, responses={200: {"content": {"text/csv": {}}}}
)
def dashboard_csv(filters: Filters, db: DbSession, actor: StatsReader):
    """Export du tableau filtré (sans date de naissance ni coordonnées) ; export journalisé."""
    data = svc.dashboard(db, filters.model_copy(update={"limit": 800}))
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    cols = [
        "full_name",
        "display_name",
        "position",
        "age",
        "region",
        "shirt_number",
        *ts.STAT_FIELDS,
    ]
    w.writerow(["team", *cols, "goals_per_90", "avg_rating"])
    for r in data.rows:
        w.writerow(
            [r.team.name, *(getattr(r, c) for c in cols), r.goals_per_90 or "", r.avg_rating or ""]
        )
    audit.record(
        db,
        actor,
        "export",
        "talents",
        None,
        {"rows": len(data.rows), **filters.model_dump(mode="json")},
    )
    db.commit()
    return Response(
        "\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="talents.csv"'},
    )


@router.get("/admin/talents/{person_id}", response_model=ts.TalentProfile)
def profile(person_id: uuid.UUID, db: DbSession, actor: Scout):
    out = svc.profile(db, actor, person_id)
    db.commit()  # consultation des notes journalisée
    return out


@router.put("/admin/talents/{person_id}/watch", status_code=status.HTTP_204_NO_CONTENT)
def watch(person_id: uuid.UUID, body: ts.WatchIn, db: DbSession, actor: Scout):
    svc.set_watch(db, actor, person_id, body)
    db.commit()


@router.post("/admin/talents/{person_id}/notes", status_code=status.HTTP_201_CREATED)
def add_note(person_id: uuid.UUID, body: ts.NoteIn, db: DbSession, actor: Scout) -> dict:
    svc.add_note(db, actor, person_id, body)
    db.commit()
    return {"ok": True}


@router.post("/admin/talent-notes/{note_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: uuid.UUID, body: ts.NoteDelete, db: DbSession, actor: Scout):
    svc.delete_note(db, actor, note_id, body.reason)
    db.commit()
