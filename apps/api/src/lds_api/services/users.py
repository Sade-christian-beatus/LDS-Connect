"""Gestion des comptes : création, modification, désactivation, mots de passe.

Pas de mot de passe choisi par l'administrateur : un mot de passe provisoire est généré,
affiché une seule fois, puis l'utilisateur le change depuis « Mon compte ».
"""

import re
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from lds_api.core.errors import BusinessError, NotFound
from lds_api.core.security import hash_password, verify_password
from lds_api.models import RefreshToken, Role, Team, User, user_roles
from lds_api.models.enums import RoleCode
from lds_api.services import audit

MIN_PASSWORD_LENGTH = 12
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Sans caractères ambigus (0/O, 1/l/I) : lisible quand on le dicte ou le recopie
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def temporary_password() -> str:
    """Ex. « K7Pq-W9xA-m3Tz-hR4c » : 16 caractères aléatoires (≈ 92 bits)."""
    groups = ["".join(secrets.choice(_ALPHABET) for _ in range(4)) for _ in range(4)]
    return "-".join(groups)


def get_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("Compte")
    return user


def _role(db: Session, code: RoleCode) -> Role:
    role = db.scalar(select(Role).where(Role.code == code))
    if role is None:
        raise BusinessError("Rôle inconnu")
    return role


def _check_team(db: Session, role: RoleCode, team_id: uuid.UUID | None) -> uuid.UUID | None:
    if role == RoleCode.GESTIONNAIRE_CLUB:
        if team_id is None or db.get(Team, team_id) is None:
            raise BusinessError("Un gestionnaire de club doit être rattaché à une équipe")
        return team_id
    return None  # les autres rôles ne sont pas limités à une équipe


def _active_super_admins(db: Session) -> int:
    return db.scalar(
        select(func.count(User.id))
        .join(user_roles, user_roles.c.user_id == User.id)
        .join(Role, Role.id == user_roles.c.role_id)
        .where(Role.code == RoleCode.SUPER_ADMIN, User.is_active.is_(True))
    )


def revoke_sessions(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


def create(db: Session, actor, *, email: str, full_name: str, role: RoleCode, team_id):
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise BusinessError("Adresse e-mail invalide", code="invalid_email")
    if db.scalar(select(User.id).where(User.email == email)):
        raise BusinessError("Un compte existe déjà avec cette adresse", code="duplicate_email")
    password = temporary_password()
    user = User(
        email=email,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        roles=[_role(db, role)],
        team_id=_check_team(db, role, team_id),
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    audit.record(db, actor, "create", "user", user.id, {"email": email, "role": role})
    return user, password


def update_user(db: Session, actor, user: User, data: dict) -> User:
    role = RoleCode(data["role"]) if data.get("role") else next(iter(user.role_codes), None)
    is_super = RoleCode.SUPER_ADMIN in user.role_codes
    loses_super = is_super and (
        (data.get("role") and role != RoleCode.SUPER_ADMIN) or data.get("is_active") is False
    )
    if user.id == actor.id and (loses_super or data.get("is_active") is False):
        raise BusinessError(
            "Vous ne pouvez pas retirer vos propres droits ni désactiver votre compte"
        )
    if loses_super and user.is_active and _active_super_admins(db) <= 1:
        raise BusinessError("Il doit rester au moins un super administrateur actif")

    before = {
        "full_name": user.full_name,
        "role": sorted(r.value for r in user.role_codes),
        "team_id": user.team_id,
        "is_active": user.is_active,
    }
    if "full_name" in data and data["full_name"]:
        user.full_name = data["full_name"].strip()
    if "role" in data or "team_id" in data:
        user.roles = [_role(db, role)]
        user.team_id = _check_team(db, role, data.get("team_id", user.team_id))
    if "is_active" in data and data["is_active"] is not None:
        user.is_active = data["is_active"]
        if not user.is_active:
            revoke_sessions(db, user.id)
    after = {
        "full_name": user.full_name,
        "role": sorted(r.value for r in user.role_codes),
        "team_id": user.team_id,
        "is_active": user.is_active,
    }
    changes = {k: [before[k], after[k]] for k in before if before[k] != after[k]}
    if changes:
        audit.record(db, actor, "update", "user", user.id, changes)
    return user


def reset_password(db: Session, actor, user: User) -> str:
    password = temporary_password()
    user.password_hash = hash_password(password)
    user.must_change_password = True
    revoke_sessions(db, user.id)
    audit.record(db, actor, "reset_password", "user", user.id)
    return password


def change_own_password(db: Session, actor, current: str, new: str) -> None:
    user = actor.user
    if not verify_password(user.password_hash, current):
        raise BusinessError("Mot de passe actuel incorrect", code="wrong_password")
    if len(new) < MIN_PASSWORD_LENGTH:
        raise BusinessError(
            f"Le nouveau mot de passe doit faire au moins {MIN_PASSWORD_LENGTH} caractères",
            code="weak_password",
        )
    if new == current:
        raise BusinessError("Le nouveau mot de passe doit être différent de l'actuel")
    user.password_hash = hash_password(new)
    user.must_change_password = False
    revoke_sessions(db, user.id)  # les autres appareils devront se reconnecter
    audit.record(db, actor, "change_password", "user", user.id)


def active_delegates(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .join(user_roles, user_roles.c.user_id == User.id)
            .join(Role, Role.id == user_roles.c.role_id)
            .where(Role.code == RoleCode.DELEGUE_MATCH, User.is_active.is_(True))
            .order_by(User.full_name)
        )
    )
