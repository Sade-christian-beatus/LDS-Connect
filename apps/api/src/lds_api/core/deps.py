"""Dépendances FastAPI : session, utilisateur courant, permissions, contexte de requête."""

import ipaddress
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from lds_api.core.config import get_settings
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


@lru_cache
def _trusted_networks(spec: str) -> tuple[ipaddress._BaseNetwork, ...]:
    nets = []
    for item in filter(None, (x.strip() for x in spec.split(","))):
        nets.append(ipaddress.ip_network(item, strict=False))
    return tuple(nets)


def _is_trusted(host: str, nets) -> bool:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(addr in n for n in nets)


def client_ip(request: Request) -> str | None:
    """Adresse du visiteur. Derrière un proxy de confiance, on lit X-Forwarded-For de droite
    à gauche et on retient la première adresse qui n'est pas un proxy de confiance : un
    visiteur ne peut pas se faire passer pour un autre en ajoutant l'en-tête lui-même."""
    peer = request.client.host if request.client else None
    nets = _trusted_networks(get_settings().trusted_proxies)
    if not peer or not _is_trusted(peer, nets):
        return peer
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return peer
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    for hop in reversed(hops):
        if not _is_trusted(hop, nets):
            try:
                return str(ipaddress.ip_address(hop))
            except ValueError:
                return peer
    return hops[0] if hops else peer


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
        if actor.user.must_change_password:
            # Seuls « Mon compte » (/auth/me, /auth/password) et la déconnexion restent permis
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Changez votre mot de passe provisoire avant de continuer",
                headers={"X-LDS-Reason": "password_change_required"},
            )
        missing = [p for p in perms if not actor.can(p)]
        if missing:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Action non autorisée pour votre rôle")
        return actor

    return checker


def ensure_team_scope(actor: Actor, team_id: uuid.UUID) -> None:
    """Un gestionnaire de club n'agit que sur sa propre équipe."""
    if actor.team_scoped and actor.user.team_id != team_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès limité à votre équipe")
