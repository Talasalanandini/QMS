"""add_assigned_approver_id_to_documents

Revision ID: c356ec63d55d
Revises: b042b2586350
Create Date: 2025-08-08 15:51:52.055478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c356ec63d55d'
down_revision: Union[str, Sequence[str], None] = 'b042b2586350'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add assigned_approver_id column to documents table
    op.add_column('documents', sa.Column('assigned_approver_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'documents', 'employees', ['assigned_approver_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove assigned_approver_id column from documents table
    op.drop_constraint(None, 'documents', type_='foreignkey')
    op.drop_column('documents', 'assigned_approver_id')
