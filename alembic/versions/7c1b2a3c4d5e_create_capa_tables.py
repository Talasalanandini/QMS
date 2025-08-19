"""create CAPA tables

Revision ID: 7c1b2a3c4d5e
Revises: fa3b0f579a40
Create Date: 2025-08-18 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision: str = '7c1b2a3c4d5e'
down_revision: Union[str, Sequence[str], None] = 'fa3b0f579a40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types if not already present
    op.execute("""
    DO $$ BEGIN
        CREATE TYPE capaissuetypeenum AS ENUM ('Deviation', 'Non-Conformance', 'Customer Complaint', 'Audit Finding', 'Process Improvement', 'Quality Issue', 'Documentation Error');
    EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
    DO $$ BEGIN
        CREATE TYPE capapriorityenum AS ENUM ('Low', 'Medium', 'High', 'Critical');
    EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
    DO $$ BEGIN
        CREATE TYPE capastatusenum AS ENUM ('OPEN', 'IN PROGRESS', 'PENDING VERIFICATION', 'CLOSED', 'SENT BACK');
    EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)

    issue_enum = ENUM(name='capaissuetypeenum', create_type=False)
    priority_enum = ENUM(name='capapriorityenum', create_type=False)
    status_enum = ENUM(name='capastatusenum', create_type=False)

    # CAPA table
    op.create_table(
        'capas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('capa_code', sa.String(), nullable=False),
        sa.Column('issue_title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('issue_type', issue_enum, nullable=False),
        sa.Column('priority', priority_enum, nullable=False, server_default='Medium'),
        sa.Column('status', status_enum, nullable=False, server_default='OPEN'),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('started_date', sa.DateTime(), nullable=True),
        sa.Column('completed_date', sa.DateTime(), nullable=True),
        sa.Column('closed_date', sa.DateTime(), nullable=True),
        sa.Column('action_taken', sa.Text(), nullable=True),
        sa.Column('completion_notes', sa.Text(), nullable=True),
        sa.Column('evidence_files', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by'], ['employees.id']),
        sa.ForeignKeyConstraint(['assigned_to'], ['employees.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_capas_id'), 'capas', ['id'], unique=False)
    op.create_index('uq_capas_capa_code', 'capas', ['capa_code'], unique=True)

    # CAPA history table
    op.create_table(
        'capa_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('capa_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('performed_by_id', sa.Integer(), nullable=False),
        sa.Column('previous_status', status_enum, nullable=True),
        sa.Column('new_status', status_enum, nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('performed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['capa_id'], ['capas.id']),
        sa.ForeignKeyConstraint(['performed_by_id'], ['employees.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_capa_history_id'), 'capa_history', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_capa_history_id'), table_name='capa_history')
    op.drop_table('capa_history')

    op.drop_index('uq_capas_capa_code', table_name='capas')
    op.drop_index(op.f('ix_capas_id'), table_name='capas')
    op.drop_table('capas')

    # Drop enums (ignore if other tables still depend on them)
    op.execute("DROP TYPE IF EXISTS capaissuetypeenum")
    op.execute("DROP TYPE IF EXISTS capapriorityenum")
    op.execute("DROP TYPE IF EXISTS capastatusenum")
