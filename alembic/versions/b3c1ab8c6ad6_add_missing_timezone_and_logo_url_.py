"""add_missing_timezone_and_logo_url_columns

Revision ID: b3c1ab8c6ad6
Revises: 8e3e9f134056
Create Date: 2025-08-11 11:13:39.577457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c1ab8c6ad6'
down_revision: Union[str, Sequence[str], None] = '8e3e9f134056'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add the missing timezone and logo_url columns to clients table
    op.add_column('clients', sa.Column('timezone', sa.String(), nullable=True, server_default='UTC'))
    op.add_column('clients', sa.Column('logo_url', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the added columns
    op.drop_column('clients', 'logo_url')
    op.drop_column('clients', 'timezone')
