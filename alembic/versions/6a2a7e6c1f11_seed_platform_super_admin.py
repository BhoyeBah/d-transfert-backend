"""seed platform super admin

Revision ID: 6a2a7e6c1f11
Revises: d6e2f4a8c901
Create Date: 2026-07-06 00:00:00.000000

"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6a2a7e6c1f11"
down_revision: Union[str, Sequence[str], None] = "d6e2f4a8c901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADMIN_MATRICULE = "contact@platform.com"
ADMIN_FULL_NAME = "Platform Admin"
ADMIN_PHONE = "+00000000000"
ADMIN_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$PqeU8h5DqFXqvVeq9d6bUw$dbhX2JxVV/QA2WZ1gBAmXGpTTPkKRDZ4TONWzpBtvII"
ADMIN_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "d-transfert-platform-super-admin")


def upgrade() -> None:
    """Seed a platform super admin account for direct platform login."""
    op.execute(
        sa.text(
            """
            INSERT INTO users (
                id,
                company_id,
                role_id,
                matricule,
                full_name,
                phone,
                password_hash,
                is_owner,
                is_super_admin,
                is_active,
                failed_login_attempts,
                locked_until,
                last_login_at
            )
            SELECT
                :id,
                NULL,
                r.id,
                :matricule,
                :full_name,
                :phone,
                :password_hash,
                FALSE,
                TRUE,
                TRUE,
                0,
                NULL,
                NULL
            FROM roles AS r
            WHERE r.code = 'super_admin'
            ON CONFLICT (matricule) DO NOTHING
            """
        ),
        {
            "id": str(ADMIN_ID),
            "matricule": ADMIN_MATRICULE,
            "full_name": ADMIN_FULL_NAME,
            "phone": ADMIN_PHONE,
            "password_hash": ADMIN_PASSWORD_HASH,
        },
    )


def downgrade() -> None:
    """Remove the seeded platform super admin account."""
    op.execute(sa.text("DELETE FROM users WHERE matricule = :matricule"), {"matricule": ADMIN_MATRICULE})
