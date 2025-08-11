"""add missing audit fields

Revision ID: add_missing_audit_fields
Revises: ec83fd106589
Create Date: 2025-01-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_missing_audit_fields'
down_revision: Union[str, Sequence[str], None] = 'ec83fd106589'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add missing fields to audits table
    op.add_column('audits', sa.Column('end_date', sa.DateTime(), nullable=True))
    op.add_column('audits', sa.Column('target_department', sa.String(), nullable=True))
    op.add_column('audits', sa.Column('observations', sa.Text(), nullable=True))
    op.add_column('audits', sa.Column('findings', sa.Text(), nullable=True))
    op.add_column('audits', sa.Column('recommendations', sa.Text(), nullable=True))
    op.add_column('audits', sa.Column('completed_at', sa.DateTime(), nullable=True))
    op.add_column('audits', sa.Column('signature', sa.String(), nullable=True))
    op.add_column('audits', sa.Column('signed_date', sa.DateTime(), nullable=True))
    op.add_column('audits', sa.Column('auditor_name', sa.String(), nullable=True))
    op.add_column('audits', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('audits', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the added fields
    op.drop_column('audits', 'auditor_name')
    op.drop_column('audits', 'signed_date')
    op.drop_column('audits', 'signature')
    op.drop_column('audits', 'completed_at')
    op.drop_column('audits', 'recommendations')
    op.drop_column('audits', 'findings')
    op.drop_column('audits', 'observations')
    op.drop_column('audits', 'target_department')
    op.drop_column('audits', 'end_date')
    op.drop_column('audits', 'updated_at')
    op.drop_column('audits', 'created_at') 