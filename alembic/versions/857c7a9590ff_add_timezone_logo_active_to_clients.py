"""add_timezone_logo_active_to_clients

Revision ID: 857c7a9590ff
Revises: 47ac1453790b
Create Date: 2025-08-11 10:52:19.991927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '857c7a9590ff'
down_revision: Union[str, Sequence[str], None] = '47ac1453790b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns to clients table
    op.add_column('clients', sa.Column('timezone', sa.String(), nullable=True, server_default='UTC'))
    op.add_column('clients', sa.Column('logo_url', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns from clients table
    op.drop_column('clients', 'is_active')
    op.drop_column('clients', 'logo_url')
    op.drop_column('clients', 'timezone')
