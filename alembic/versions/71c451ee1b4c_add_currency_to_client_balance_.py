"""add currency to client_balance_movements

Revision ID: 71c451ee1b4c
Revises: 0118c9af488b
Create Date: 2026-07-11 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71c451ee1b4c'
down_revision: Union[str, Sequence[str], None] = '0118c9af488b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('client_balance_movements', sa.Column('currency', sa.String(length=8), nullable=True))

    # Backfill from the originating transfer/payment (source_type/source_id), which is
    # always the same currency for every movement sharing that source. Fall back to the
    # client's company default_currency for any row we can't resolve (should not happen
    # in practice, but keeps the NOT NULL constraint safe).
    op.execute(
        """
        UPDATE client_balance_movements m
        SET currency = t.currency
        FROM transfers t
        WHERE m.source_id = t.id
          AND m.source_type IN ('transfer', 'transfer_reversal')
          AND m.currency IS NULL
        """
    )
    op.execute(
        """
        UPDATE client_balance_movements m
        SET currency = p.currency
        FROM payments p
        WHERE m.source_id = p.id
          AND m.source_type IN ('payment', 'payment_reversal')
          AND m.currency IS NULL
        """
    )
    op.execute(
        """
        UPDATE client_balance_movements m
        SET currency = c.default_currency
        FROM clients cl
        JOIN companies c ON c.id = cl.company_id
        WHERE m.client_id = cl.id
          AND m.currency IS NULL
        """
    )

    op.alter_column('client_balance_movements', 'currency', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('client_balance_movements', 'currency')
