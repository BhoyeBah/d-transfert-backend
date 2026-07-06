"""rename platform super admin matricule

Revision ID: 1f3d2b8a7c44
Revises: 6a2a7e6c1f11
Create Date: 2026-07-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1f3d2b8a7c44"
down_revision: Union[str, Sequence[str], None] = "6a2a7e6c1f11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_MATRICULE = "contact@platform.com"
NEW_MATRICULE = "MAT-AD-001"


def upgrade() -> None:
    """Rename the seeded platform admin matricule."""
    op.get_bind().execute(
        sa.text(
            """
            UPDATE users
            SET matricule = :new_matricule
            WHERE matricule = :old_matricule
            """
        ),
        {"old_matricule": OLD_MATRICULE, "new_matricule": NEW_MATRICULE},
    )


def downgrade() -> None:
    """Restore the previous seeded platform admin matricule."""
    op.get_bind().execute(
        sa.text(
            """
            UPDATE users
            SET matricule = :old_matricule
            WHERE matricule = :new_matricule
            """
        ),
        {"old_matricule": OLD_MATRICULE, "new_matricule": NEW_MATRICULE},
    )
