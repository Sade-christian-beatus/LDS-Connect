"""Utilisateurs, rôles et jetons de rafraîchissement."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy import false as sa_false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lds_api.db.base import Base, Timestamps, UUIDPk
from lds_api.models.enums import RoleCode, str_enum

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(UUIDPk, Base):
    __tablename__ = "roles"

    code: Mapped[RoleCode] = mapped_column(str_enum(RoleCode), unique=True)
    label: Mapped[str] = mapped_column(String(80))


class User(UUIDPk, Timestamps, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(254), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Pour le rôle gestionnaire_club : périmètre limité à cette équipe
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Mot de passe provisoire (création, réinitialisation) : à changer avant toute autre action
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sa_false(), nullable=False
    )

    roles: Mapped[list[Role]] = relationship(secondary=user_roles, lazy="selectin")

    @property
    def role_codes(self) -> set[RoleCode]:
        return {r.code for r in self.roles}


class RefreshToken(Base):
    """Jeton de rafraîchissement (rotation à chaque usage, révocable)."""

    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    family_id: Mapped[str] = mapped_column(String(64), index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
