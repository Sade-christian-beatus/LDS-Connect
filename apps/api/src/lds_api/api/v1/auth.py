"""Authentification : connexion, rafraîchissement, déconnexion, profil."""

import uuid

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from lds_api.core import ratelimit
from lds_api.core.config import get_settings
from lds_api.core.deps import CurrentActor, DbSession, client_ip
from lds_api.services import auth as auth_service
from lds_api.services import mfa

router = APIRouter(prefix="/auth", tags=["authentification"])

REFRESH_COOKIE = "lds_refresh"
REFRESH_PATH = "/api/v1/auth"


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    roles: list[str]
    permissions: list[str]
    team_id: uuid.UUID | None
    must_change_password: bool
    mfa_enabled: bool = False
    mfa_required: bool = False
    # Double authentification exigée pour ce rôle mais pas encore activée
    mfa_setup_required: bool = False


class MfaRequiredOut(BaseModel):
    """Mot de passe correct : saisir le code de l'application d'authentification."""

    mfa_required: bool = True
    mfa_token: str


class MfaLoginIn(BaseModel):
    mfa_token: str = Field(max_length=2000)
    code: str = Field(min_length=6, max_length=12)


class MfaCodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=12)


class MfaSetupOut(BaseModel):
    secret: str
    otpauth_uri: str
    qr_svg: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 — type de jeton OAuth2, pas un secret
    expires_in: int
    user: UserOut


def _user_out(actor_or_user) -> UserOut:
    from lds_api.core.rbac import permissions_for

    user = getattr(actor_or_user, "user", actor_or_user)
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=sorted(r.value for r in user.role_codes),
        permissions=sorted(p.value for p in permissions_for(user.role_codes)),
        team_id=user.team_id,
        must_change_password=user.must_change_password,
        mfa_enabled=mfa.enabled(user),
        mfa_required=mfa.required_for(user),
        mfa_setup_required=mfa.setup_pending(user),
    )


def _respond(response: Response, pair: auth_service.TokenPair) -> TokenOut:
    s = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        pair.refresh_token,
        max_age=s.jwt_refresh_ttl_days * 86400,
        httponly=True,
        secure=s.refresh_cookie_secure,
        samesite="strict",
        path=REFRESH_PATH,
    )
    return TokenOut(
        access_token=pair.access_token,
        expires_in=s.jwt_access_ttl_minutes * 60,
        user=_user_out(pair.user),
    )


@router.post("/login", response_model=TokenOut | MfaRequiredOut)
def login(
    body: LoginIn, request: Request, response: Response, db: DbSession
) -> TokenOut | MfaRequiredOut:
    ip = client_ip(request)
    key = f"login:{ip}:{body.email.lower()}"
    ratelimit.hit(key, limit=10, window_seconds=300)
    try:
        pair = auth_service.login(
            db, body.email, body.password, ip=ip, user_agent=request.headers.get("user-agent")
        )
    except auth_service.AuthError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Adresse e-mail ou mot de passe incorrect"
        ) from None
    ratelimit.reset(key)
    if isinstance(pair, auth_service.MfaChallenge):
        return MfaRequiredOut(mfa_token=pair.mfa_token)
    return _respond(response, pair)


@router.post("/login/mfa", response_model=TokenOut)
def login_mfa(body: MfaLoginIn, request: Request, response: Response, db: DbSession) -> TokenOut:
    ip = client_ip(request)
    # 5 essais par jeton de connexion et par adresse (code à 6 chiffres)
    key = f"mfa:{ip}:{body.mfa_token[-24:]}"
    ratelimit.hit(key, limit=5, window_seconds=300)
    try:
        pair = auth_service.login_mfa(
            db, body.mfa_token, body.code, ip=ip, user_agent=request.headers.get("user-agent")
        )
    except auth_service.AuthError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Code incorrect ou expiré : reconnectez-vous si besoin"
        ) from None
    return _respond(response, pair)


@router.post("/mfa/setup", response_model=MfaSetupOut)
def mfa_setup(actor: CurrentActor, db: DbSession) -> MfaSetupOut:
    out = mfa.start_setup(db, actor, actor.user)
    db.commit()
    return MfaSetupOut(**out)


@router.post("/mfa/enable", response_model=UserOut)
def mfa_enable(body: MfaCodeIn, actor: CurrentActor, db: DbSession) -> UserOut:
    mfa.enable(db, actor, actor.user, body.code)
    db.commit()
    return _user_out(actor)


@router.post("/mfa/disable", response_model=UserOut)
def mfa_disable(body: MfaCodeIn, actor: CurrentActor, db: DbSession) -> UserOut:
    mfa.disable(db, actor, actor.user, body.code)
    db.commit()
    return _user_out(actor)


@router.post("/refresh", response_model=TokenOut)
def refresh(
    request: Request,
    response: Response,
    db: DbSession,
    lds_refresh: str | None = Cookie(default=None),
) -> TokenOut:
    if not lds_refresh:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expirée")
    try:
        pair = auth_service.refresh(db, lds_refresh, user_agent=request.headers.get("user-agent"))
    except auth_service.AuthError:
        response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expirée") from None
    return _respond(response, pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, db: DbSession, lds_refresh: str | None = Cookie(default=None)):
    auth_service.logout(db, lds_refresh)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)


@router.get("/me", response_model=UserOut)
def me(actor: CurrentActor) -> UserOut:
    return _user_out(actor)
