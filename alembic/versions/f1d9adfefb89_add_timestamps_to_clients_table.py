"""add_timestamps_to_clients_table

Revision ID: f1d9adfefb89
Revises: 3136e1eed414
Create Date: 2025-08-11 12:11:49.227017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1d9adfefb89'
down_revision: Union[str, Sequence[str], None] = '3136e1eed414'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add created_at and updated_at columns to clients table."""
    op.add_column('clients', sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
    op.add_column('clients', sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))

def downgrade() -> None:
    """Remove created_at and updated_at columns from clients table."""
    op.drop_column('clients', 'updated_at')
    op.drop_column('clients', 'created_at')
