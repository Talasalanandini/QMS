"""remove_unnecessary_fields_from_clients

Revision ID: 03af88e29153
Revises: 857c7a9590ff
Create Date: 2025-08-11 11:00:24.573944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03af88e29153'
down_revision: Union[str, Sequence[str], None] = '857c7a9590ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove unnecessary columns from clients table
    op.drop_column('clients', 'country')
    op.drop_column('clients', 'created_at')
    op.drop_column('clients', 'updated_at')
    op.drop_column('clients', 'deleted_at')


def downgrade() -> None:
    """Downgrade schema."""
    # Add back the removed columns
    op.add_column('clients', sa.Column('country', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('clients', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('clients', sa.Column('deleted_at', sa.DateTime(), nullable=True))
