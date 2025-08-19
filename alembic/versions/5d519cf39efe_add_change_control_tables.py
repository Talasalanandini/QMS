"""add_change_control_tables

Revision ID: 5d519cf39efe
Revises: 68392d1e459c
Create Date: 2025-08-13 12:53:43.232477

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d519cf39efe'
down_revision: Union[str, Sequence[str], None] = '68392d1e459c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create change control tables."""
    # Create enum types only if they don't exist
    op.execute("DO $$ BEGIN CREATE TYPE changetypeenum AS ENUM ('Document', 'Workflow', 'Training'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE changestatusenum AS ENUM ('Submitted', 'Reviewed', 'Approved', 'Rejected'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    
    # Create change_controls table
    op.create_table('change_controls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('change_type', sa.Enum('Document', 'Workflow', 'Training', name='changetypeenum', create_type=False), nullable=False),
        sa.Column('related_document_id', sa.Integer(), nullable=True),
        sa.Column('reviewer_id', sa.Integer(), nullable=False),
        sa.Column('approver_id', sa.Integer(), nullable=False),
        sa.Column('requester_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('Submitted', 'Reviewed', 'Approved', 'Rejected', name='changestatusenum', create_type=False), nullable=False, server_default='Submitted'),
        sa.Column('review_comments', sa.Text(), nullable=True),
        sa.Column('approval_comments', sa.Text(), nullable=True),
        sa.Column('review_date', sa.DateTime(), nullable=True),
        sa.Column('approval_date', sa.DateTime(), nullable=True),
        sa.Column('implementation_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['related_document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['reviewer_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['approver_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['requester_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_change_controls_id'), 'change_controls', ['id'], unique=False)
    
    # Create change_control_history table
    op.create_table('change_control_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('change_control_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('performed_by_id', sa.Integer(), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('previous_status', sa.Enum('Submitted', 'Reviewed', 'Approved', 'Rejected', name='changestatusenum', create_type=False), nullable=True),
        sa.Column('new_status', sa.Enum('Submitted', 'Reviewed', 'Approved', 'Rejected', name='changestatusenum', create_type=False), nullable=True),
        sa.Column('performed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['change_control_id'], ['change_controls.id'], ),
        sa.ForeignKeyConstraint(['performed_by_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_change_control_history_id'), 'change_control_history', ['id'], unique=False)


def downgrade() -> None:
    """Drop change control tables."""
    op.drop_index(op.f('ix_change_control_history_id'), table_name='change_control_history')
    op.drop_table('change_control_history')
    op.drop_index(op.f('ix_change_controls_id'), table_name='change_controls')
    op.drop_table('change_controls')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS changestatusenum")
    op.execute("DROP TYPE IF EXISTS changetypeenum")
