"""add_company_training_assignments_table

Revision ID: 3136e1eed414
Revises: e7b399419ef9
Create Date: 2025-08-11 11:31:38.900105

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3136e1eed414'
down_revision: Union[str, Sequence[str], None] = 'e7b399419ef9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create company_training_assignments table
    op.create_table('company_training_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('training_id', sa.Integer(), nullable=False),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.Column('assigned_date', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['training_id'], ['trainings.id'], ),
        sa.ForeignKeyConstraint(['assigned_by'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_company_training_assignments_id'), 'company_training_assignments', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop company_training_assignments table
    op.drop_index(op.f('ix_company_training_assignments_id'), table_name='company_training_assignments')
    op.drop_table('company_training_assignments')
