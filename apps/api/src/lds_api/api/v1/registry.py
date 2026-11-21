"""Back-office du registre : équipes, effectifs, joueurs, encadreurs."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select

from lds_api.core.deps import Actor, DbSession, ensure_team_scope, require
from lds_api.core.errors import NotFound
from lds_api.core.rbac import Perm
from lds_api.models import AuditLog, Person, Team
from lds_api.models.enums import MembershipKind
from lds_api.schemas import registry as s
from lds_api.services import audit, registry, seasons

router = APIRouter(prefix="/admin", tags=["registre"])


@router.get("/teams/overview", response_model=list[s.TeamOverview])
def teams_overview(
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.SQUAD_READ))],
):
    """Synthèse de toutes les équipes (un gestionnaire de club ne voit que la sienne)."""
    teams = db.scalars(select(Team).order_by(Team.name))
    if actor.team_scoped:
        teams = [t for t in teams if t.id == actor.user.team_id]
    return [registry.overview(db, t) for t in teams]


@router.get("/audit", response_model=list[s.AuditEntry])
def audit_log(
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.AUDIT_READ))],
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    before_id: Annotated[
        int | None, Query(description="Pagination : entrées plus anciennes")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    """Journal d'audit, du plus récent au plus ancien."""
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditLog.entity_id == entity_id)
    if action:
        q = q.where(AuditLog.action == action)
    if before_id:
        q = q.where(AuditLog.id < before_id)
    return list(db.scalars(q))


@router.patch("/teams/{team_id}", response_model=s.PublicTeam)
def update_team(
    team_id: uuid.UUID,
    body: s.TeamUpdate,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.TEAM_MANAGE))],
):
    team = registry.get_team(db, team_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(team, k, v)
    changes = audit.diff(team)
    if changes:
        audit.record(db, actor, "update", "team", team.id, changes)
    db.commit()
    return registry.public_team(db, team, seasons.current_season(db))


@router.get("/teams/{team_id}/squad", response_model=s.Squad)
def get_squad(
    team_id: uuid.UUID,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.SQUAD_READ))],
):
    ensure_team_scope(actor, team_id)
    return registry.squad(db, registry.get_team(db, team_id))


@router.post("/teams/{team_id}/players", status_code=status.HTTP_201_CREATED)
def create_player(
    team_id: uuid.UUID,
    body: s.PlayerCreate,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.SQUAD_WRITE))],
) -> dict:
    ensure_team_scope(actor, team_id)
    m = registry.create_player(db, actor, registry.get_team(db, team_id), body)
    db.commit()
    return {"membership_id": m.id, "person_id": m.person_id}


@router.post("/teams/{team_id}/staff", status_code=status.HTTP_201_CREATED)
def create_staff(
    team_id: uuid.UUID,
    body: s.StaffCreate,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.SQUAD_WRITE))],
) -> dict:
    ensure_team_scope(actor, team_id)
    m = registry.create_staff(db, actor, registry.get_team(db, team_id), body)
    db.commit()
    return {"membership_id": m.id, "person_id": m.person_id}


@router.patch("/players/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_player(
    person_id: uuid.UUID,
    body: s.PlayerUpdate,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.SQUAD_WRITE))],
):
    m = registry.membership_for(db, person_id)
    ensure_team_scope(actor, m.team_id)
    if m.kind != MembershipKind.PLAYER:
        raise NotFound("Joueur")
    registry.update_player(db, actor, m, body)
    db.commit()


@router.patch("/staff/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_staff(
    person_id: uuid.UUID,
    body: s.StaffUpdate,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.SQUAD_WRITE))],
):
    m = registry.membership_for(db, person_id)
    ensure_team_scope(actor, m.team_id)
    if m.kind != MembershipKind.STAFF:
        raise NotFound("Encadreur")
    registry.update_staff(db, actor, m, body)
    db.commit()


@router.post("/persons/{person_id}/release", status_code=status.HTTP_204_NO_CONTENT)
def release(
    person_id: uuid.UUID,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.SQUAD_WRITE))],
):
    m = registry.membership_for(db, person_id)
    ensure_team_scope(actor, m.team_id)
    registry.release(db, actor, m)
    db.commit()


@router.get("/persons/{person_id}/sensitive", response_model=s.SensitiveData)
def read_sensitive(
    person_id: uuid.UUID,
    db: DbSession,
    actor: Annotated[Actor, Depends(require(Perm.SENSITIVE_READ))],
):
    m = registry.membership_for(db, person_id)
    ensure_team_scope(actor, m.team_id)
    person = db.get(Person, person_id)
    out = registry.read_sensitive(db, actor, person)
    db.commit()
    return out
