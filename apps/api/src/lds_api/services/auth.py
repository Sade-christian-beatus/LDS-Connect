"""Connexion, rotation des jetons de rafraîchissement et détection de réutilisation."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from lds_api.core.config import get_settings
from lds_api.core.security import (
    create_access_token,
    create_mfa_token,
    decode_mfa_token,
    hash_password,
    needs_rehash,
    new_refresh_token_value,
    verify_password,
)
from lds_api.models import RefreshToken, User
from lds_api.services import audit

# Hachage factice : la vérification prend le même temps que l'e-mail existe ou non
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


class AuthError(Exception):
    pass


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    user: User


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        verify_password(_DUMMY_HASH, password)
        raise AuthError
    if not verify_password(user.password_hash, password) or not user.is_active:
        raise AuthError
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


def _issue(db: Session, user: User, family_id: str, user_agent: str | None) -> TokenPair:
    now = datetime.now(UTC)
    value = new_refresh_token_value()
    db.add(
        RefreshToken(
            jti=_digest(value),
            user_id=user.id,
            family_id=family_id,
            issued_at=now,
            expires_at=now + timedelta(days=get_settings().jwt_refresh_ttl_days),
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    access = create_access_token(user.id, sorted(r.value for r in user.role_codes), user.team_id)
    return TokenPair(access, value, user)


@dataclass
class MfaChallenge:
    """Mot de passe correct, code de double authentification attendu."""

    mfa_token: str


def login(
    db: Session, email: str, password: str, *, ip: str | None, user_agent: str | None
) -> "TokenPair | MfaChallenge":
    from lds_api.services import mfa

    user = authenticate(db, email, password)
    if mfa.enabled(user):
        db.commit()  # rehachage éventuel du mot de passe
        return MfaChallenge(create_mfa_token(user.id))
    return _open_session(db, user, ip=ip, user_agent=user_agent)


def login_mfa(
    db: Session, mfa_token: str, code: str, *, ip: str | None, user_agent: str | None
) -> TokenPair:
    from lds_api.services import mfa

    try:
        user = db.get(User, decode_mfa_token(mfa_token))
    except (jwt.InvalidTokenError, ValueError):
        raise AuthError from None
    if user is None or not user.is_active or not mfa.enabled(user):
        raise AuthError
    if not mfa.check_code(user, code):
        audit.record(db, _ActorStub(user, ip), "mfa_failed", "user", user.id)
        db.commit()
        raise AuthError
    return _open_session(db, user, ip=ip, user_agent=user_agent)


def _open_session(db: Session, user: User, *, ip: str | None, user_agent: str | None) -> TokenPair:
    user.last_login_at = datetime.now(UTC)
    pair = _issue(db, user, secrets.token_hex(16), user_agent)
    audit.record(db, _ActorStub(user, ip), "login", "user", user.id)
    db.commit()
    return pair


def refresh(db: Session, value: str, *, user_agent: str | None) -> TokenPair:
    """Rotation : l'ancien jeton est révoqué. Réutiliser un jeton déjà tourné révoque toute
    la famille (signe probable de vol)."""
    now = datetime.now(UTC)
    token = db.get(RefreshToken, _digest(value))
    if token is None:
        raise AuthError
    if token.revoked_at is not None:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == token.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        audit.record(db, None, "refresh_token_reuse", "user", token.user_id)
        db.commit()
        raise AuthError
    if token.expires_at < now:
        raise AuthError
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise AuthError
    pair = _issue(db, user, token.family_id, user_agent)
    token.revoked_at = now
    token.replaced_by = _digest(pair.refresh_token)
    db.commit()
    return pair


def logout(db: Session, value: str | None) -> None:
    if not value:
        return
    token = db.get(RefreshToken, _digest(value))
    if token and token.revoked_at is None:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == token.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        db.commit()


@dataclass
class _ActorStub:
    user: User
    ip: str | None
    request_id: str | None = None

    @property
    def id(self):
        return self.user.id

    @property
    def label(self) -> str:
        return f"{self.user.full_name} <{self.user.email}>"
