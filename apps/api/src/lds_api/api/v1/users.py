"""Comptes utilisateurs (super administrateur), mot de passe personnel, attribution des délégués."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from lds_api.core.deps import Actor, CurrentActor, DbSession, require
from lds_api.core.errors import BusinessError, NotFound
from lds_api.core.rbac import Perm
from lds_api.models import Match, MatchSheet, Team, User
from lds_api.models.enums import RoleCode, SheetStatus
from lds_api.services import audit, mfa, seasons
from lds_api.services import matchsheet as sheets
from lds_api.services import users as svc

router = APIRouter(tags=["comptes"])
UserManager = Annotated[Actor, Depends(require(Perm.USER_MANAGE))]
FixtureManager = Annotated[Actor, Depends(require(Perm.FIXTURE_MANAGE))]


class TeamBrief(BaseModel):
    id: uuid.UUID
    name: str


class UserAdminOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    roles: list[RoleCode]
    team: TeamBrief | None
    is_active: bool
    must_change_password: bool
    mfa_enabled: bool = False
    mfa_required: bool = False
    last_login_at: datetime | None
    created_at: datetime


class UserCreateIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    full_name: str = Field(min_length=2, max_length=120)
    role: RoleCode
    team_id: uuid.UUID | None = None


class UserUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: RoleCode | None = None
    team_id: uuid.UUID | None = None
    is_active: bool | None = None


class CredentialsOut(BaseModel):
    """Mot de passe provisoire : affiché une seule fois, jamais stocké en clair."""

    user: UserAdminOut
    temporary_password: str


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class DelegateOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str


class AssignIn(BaseModel):
    user_id: uuid.UUID | None


def _out(db, u: User) -> UserAdminOut:
    team = db.get(Team, u.team_id) if u.team_id else None
    return UserAdminOut(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        roles=sorted(u.role_codes),
        team=TeamBrief(id=team.id, name=team.name) if team else None,
        is_active=u.is_active,
        must_change_password=u.must_change_password,
        mfa_enabled=mfa.enabled(u),
        mfa_required=mfa.required_for(u),
        last_login_at=u.last_login_at,
        created_at=u.created_at,
    )


# --- Comptes (super administrateur) -----------------------------------------------
@router.get("/admin/users", response_model=list[UserAdminOut])
def list_users(db: DbSession, actor: UserManager):
    return [_out(db, u) for u in db.scalars(select(User).order_by(User.full_name))]


@router.post("/admin/users", response_model=CredentialsOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreateIn, db: DbSession, actor: UserManager):
    user, password = svc.create(
        db, actor, email=body.email, full_name=body.full_name, role=body.role, team_id=body.team_id
    )
    db.commit()
    return CredentialsOut(user=_out(db, user), temporary_password=password)


@router.patch("/admin/users/{user_id}", response_model=UserAdminOut)
def update_user(user_id: uuid.UUID, body: UserUpdateIn, db: DbSession, actor: UserManager):
    user = svc.update_user(
        db, actor, svc.get_user(db, user_id), body.model_dump(exclude_unset=True)
    )
    db.commit()
    return _out(db, user)


@router.post("/admin/users/{user_id}/reset-password", response_model=CredentialsOut)
def reset_password(user_id: uuid.UUID, db: DbSession, actor: UserManager):
    user = svc.get_user(db, user_id)
    password = svc.reset_password(db, actor, user)
    db.commit()
    return CredentialsOut(user=_out(db, user), temporary_password=password)


@router.post("/admin/users/{user_id}/reset-mfa", response_model=UserAdminOut)
def reset_mfa(user_id: uuid.UUID, db: DbSession, actor: UserManager):
    """Téléphone perdu : la double authentification est à réactiver à la prochaine connexion."""
    user = svc.get_user(db, user_id)
    if user.id == actor.user.id:
        raise BusinessError("Réinitialisez la vôtre par la commande reset-mfa du serveur")
    mfa.reset(db, actor, user)
    db.commit()
    return _out(db, user)


# --- Mon compte -------------------------------------------------------------------
@router.post("/auth/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: PasswordChangeIn, db: DbSession, actor: CurrentActor):
    svc.change_own_password(db, actor, body.current_password, body.new_password)
    db.commit()


# --- Attribution des délégués -------------------------------------------------------
@router.get("/admin/delegates", response_model=list[DelegateOut])
def list_delegates(db: DbSession, actor: FixtureManager):
    return [
        DelegateOut(id=u.id, full_name=u.full_name, email=u.email) for u in svc.active_delegates(db)
    ]


@router.get("/admin/delegate-assignments")
def delegate_assignments(db: DbSession, actor: FixtureManager) -> dict[str, DelegateOut]:
    """Délégué attribué à chaque match de la saison : {match_id: délégué}."""
    season = seasons.current_season(db)
    rows = db.execute(
        select(MatchSheet.match_id, User)
        .join(Match, Match.id == MatchSheet.match_id)
        .join(User, User.id == MatchSheet.delegate_user_id)
        .where(Match.season_id == season.id)
    ).all()
    return {str(mid): DelegateOut(id=u.id, full_name=u.full_name, email=u.email) for mid, u in rows}


@router.put("/admin/matches/{match_id}/delegate", response_model=DelegateOut | None)
def assign_delegate(match_id: uuid.UUID, body: AssignIn, db: DbSession, actor: FixtureManager):
    sheet = sheets.get_sheet(db, match_id, create=True)
    if sheet.status in (SheetStatus.VALIDATED, SheetStatus.CLOSED):
        raise BusinessError("Feuille déjà validée : l'attribution ne peut plus changer")
    delegate = None
    if body.user_id is not None:
        delegate = db.get(User, body.user_id)
        if delegate is None:
            raise NotFound("Compte")
        if not delegate.is_active or RoleCode.DELEGUE_MATCH not in delegate.role_codes:
            raise BusinessError("Ce compte n'est pas un délégué de match actif")
    before = sheet.delegate_user_id
    sheet.delegate_user_id = delegate.id if delegate else None
    audit.record(
        db,
        actor,
        "assign_delegate",
        "match",
        match_id,
        {"delegate_user_id": [before, sheet.delegate_user_id]},
    )
    db.commit()
    return (
        DelegateOut(id=delegate.id, full_name=delegate.full_name, email=delegate.email)
        if delegate
        else None
    )
