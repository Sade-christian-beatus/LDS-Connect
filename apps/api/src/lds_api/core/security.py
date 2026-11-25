"""Hachage des mots de passe (argon2id) et jetons JWT."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from lds_api.core.config import get_settings

_hasher = PasswordHasher()  # paramètres argon2id recommandés par la bibliothèque
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"  # noqa: S105 — type de jeton, pas un secret


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def _secret() -> str:
    secret = get_settings().jwt_secret.get_secret_value()
    if get_settings().environment == "production" and len(secret) < 32:
        raise RuntimeError("JWT_SECRET trop court pour la production (32 caractères minimum).")
    return secret


def create_access_token(user_id: uuid.UUID, roles: list[str], team_id: uuid.UUID | None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "roles": roles,
        "team": str(team_id) if team_id else None,
        "iat": now,
        "exp": now + timedelta(minutes=get_settings().jwt_access_ttl_minutes),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Lève jwt.InvalidTokenError si le jeton est invalide, expiré ou d'un autre type."""
    payload = jwt.decode(
        token, _secret(), algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub"]}
    )
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("Type de jeton inattendu")
    return payload


def new_refresh_token_value() -> str:
    """Valeur opaque du jeton de rafraîchissement (stockée en base par son jti)."""
    return secrets.token_urlsafe(48)


MFA_TOKEN_TYPE = "mfa"  # noqa: S105 — type de jeton, pas un secret
MFA_TOKEN_MINUTES = 5


def create_mfa_token(user_id: uuid.UUID) -> str:
    """Jeton intermédiaire : mot de passe vérifié, code de double authentification attendu."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": MFA_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=MFA_TOKEN_MINUTES),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_mfa_token(token: str) -> uuid.UUID:
    payload = jwt.decode(
        token, _secret(), algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub"]}
    )
    if payload.get("type") != MFA_TOKEN_TYPE:
        raise jwt.InvalidTokenError("Type de jeton inattendu")
    return uuid.UUID(payload["sub"])
