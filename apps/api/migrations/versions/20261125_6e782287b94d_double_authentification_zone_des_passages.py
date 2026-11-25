"""Double authentification (TOTP) des comptes et zone gardée par l'appareil de contrôle.

Audit M9 : secret chiffré, date d'activation, dernier pas de temps accepté (anti-rejeu).
Audit M10 : zone enregistrée avec chaque passage au contrôle d'accès.

Revision ID: 6e782287b94d
Revises: c48d5106f0b4
Create Date: 2026-11-25 00:34:39.536772

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6e782287b94d"
down_revision: str | Sequence[str] | None = "c48d5106f0b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("access_scans", sa.Column("zone", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("totp_secret", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("totp_enabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("totp_last_step", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "totp_last_step")
    op.drop_column("users", "totp_enabled_at")
    op.drop_column("users", "totp_secret")
    op.drop_column("access_scans", "zone")
