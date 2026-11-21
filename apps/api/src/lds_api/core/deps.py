"""Dépendances FastAPI : session, utilisateur courant, permissions, contexte de requête."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from lds_api.core.rbac import Perm, is_team_scoped, permissions_for
from lds_api.core.security import decode_access_token
from lds_api.db.session import get_db
from lds_api.models import User

DbSession = Annotated[Session, Depends(get_db)]
_bearer = HTTPBearer(auto_error=False)


@dataclass
class Actor:
    """Utilisateur authentifié et contexte de la requête (pour l'audit)."""

    user: User
    ip: str | None
    request_id: str | None

    @property
    def id(self) -> uuid.UUID:
        return self.user.id

    @property
    def label(self) -> str:
        return f"{self.user.full_name} <{self.user.email}>"

    @property
    def permissions(self) -> frozenset[Perm]:
        return permissions_for(self.user.role_codes)

    def can(self, perm: Perm) -> bool:
        return perm in self.permissions

    @property
    def team_scoped(self) -> bool:
        return is_team_scoped(self.user.role_codes)


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def get_current_actor(
    request: Request,
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Actor:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Authentification requise",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized
    try:
        payload = decode_access_token(creds.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise unauthorized from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return Actor(user=user, ip=client_ip(request), request_id=request.headers.get("x-request-id"))


CurrentActor = Annotated[Actor, Depends(get_current_actor)]


def require(*perms: Perm) -> Callable[[Actor], Actor]:
    """Dépendance : l'utilisateur doit détenir toutes les permissions indiquées."""

    def checker(actor: CurrentActor) -> Actor:
        missing = [p for p in perms if not actor.can(p)]
        if missing:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Action non autorisée pour votre rôle")
        return actor

    return checker


def ensure_team_scope(actor: Actor, team_id: uuid.UUID) -> None:
    """Un gestionnaire de club n'agit que sur sa propre équipe."""
    if actor.team_scoped and actor.user.team_id != team_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès limité à votre équipe")
