"""recreate_clients_table_with_only_required_columns

Revision ID: e7b399419ef9
Revises: b3c1ab8c6ad6
Create Date: 2025-08-11 11:16:06.293004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b399419ef9'
down_revision: Union[str, Sequence[str], None] = 'b3c1ab8c6ad6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the existing clients table completely
    op.drop_table('clients')
    
    # Recreate the clients table with only the required columns
    op.create_table('clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(), nullable=False),
        sa.Column('timezone', sa.String(), nullable=True, server_default='UTC'),
        sa.Column('logo_url', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clients_id'), 'clients', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the recreated table
    op.drop_index(op.f('ix_clients_id'), table_name='clients')
    op.drop_table('clients')
    
    # Recreate the original table structure
    op.create_table('clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(), nullable=False),
        sa.Column('industry', sa.String(), nullable=False),
        sa.Column('contact_email', sa.String(), nullable=False),
        sa.Column('contact_phone', sa.String(), nullable=True),
        sa.Column('country', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clients_id'), 'clients', ['id'], unique=False)
