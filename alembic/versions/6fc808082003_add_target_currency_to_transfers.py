"""add target_currency to transfers

Revision ID: 6fc808082003
Revises: e36e0ea2c8df
Create Date: 2026-07-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6fc808082003'
down_revision: Union[str, Sequence[str], None] = 'e36e0ea2c8df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('transfers', sa.Column('target_currency', sa.String(length=8), nullable=True))
    # Historique : la devise cible valait toujours celle de la collaboration (le champ n'existait
    # pas encore) — on le rétro-remplit ainsi pour ne rien changer au comportement des envois
    # déjà créés.
    op.execute(
        """
        UPDATE transfers
        SET target_currency = collaborations.currency
        FROM collaborations
        WHERE transfers.collaboration_id = collaborations.id
        """
    )
    op.alter_column('transfers', 'target_currency', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('transfers', 'target_currency')
