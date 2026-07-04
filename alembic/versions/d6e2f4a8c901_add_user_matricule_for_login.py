"""add user matricule for login

Revision ID: d6e2f4a8c901
Revises: 5a5893ceeb22
Create Date: 2026-07-04 15:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d6e2f4a8c901"
down_revision: Union[str, Sequence[str], None] = "5a5893ceeb22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("matricule", sa.String(length=32), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE users AS u
            SET matricule = c.registration_code
            FROM companies AS c
            WHERE u.company_id = c.id AND u.is_owner IS TRUE
            """
        )
    )
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    u.id,
                    c.registration_code,
                    row_number() OVER (
                        PARTITION BY u.company_id
                        ORDER BY u.created_at, u.id
                    ) AS rn
                FROM users AS u
                JOIN companies AS c ON c.id = u.company_id
                WHERE u.company_id IS NOT NULL AND u.is_owner IS FALSE
            )
            UPDATE users AS u
            SET matricule = ranked.registration_code || '-EMP' || lpad(ranked.rn::text, 3, '0')
            FROM ranked
            WHERE u.id = ranked.id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET matricule = 'SA-' || upper(substr(replace(id::text, '-', ''), 1, 12))
            WHERE matricule IS NULL AND is_super_admin IS TRUE
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET matricule = 'USR-' || upper(substr(replace(id::text, '-', ''), 1, 12))
            WHERE matricule IS NULL
            """
        )
    )

    op.alter_column("users", "matricule", nullable=False)
    op.create_unique_constraint("uq_user_matricule", "users", ["matricule"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_user_matricule", "users", type_="unique")
    op.drop_column("users", "matricule")
