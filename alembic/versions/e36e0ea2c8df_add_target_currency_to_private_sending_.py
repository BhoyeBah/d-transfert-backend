"""add target_currency to private_sending_rates

Revision ID: e36e0ea2c8df
Revises: 7ad4b4f19fbe
Create Date: 2026-07-14 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e36e0ea2c8df'
down_revision: Union[str, Sequence[str], None] = '7ad4b4f19fbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # NULL = "toutes destinations" (comportement historique d'un taux créé sans devise cible) —
    # les taux déjà enregistrés restent donc NULL, exactement équivalents à avant ce champ.
    op.add_column('private_sending_rates', sa.Column('target_currency', sa.String(length=8), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('private_sending_rates', 'target_currency')
