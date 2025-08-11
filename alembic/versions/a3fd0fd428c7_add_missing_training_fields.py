"""add missing training fields

Revision ID: a3fd0fd428c7
Revises: ccedc5c3c272
Create Date: 2025-08-06 13:05:40.038425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3fd0fd428c7'
down_revision: Union[str, Sequence[str], None] = 'ccedc5c3c272'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add missing columns to trainings table
    op.add_column('trainings', sa.Column('course_code', sa.String(), nullable=True))
    op.add_column('trainings', sa.Column('passing_score', sa.Integer(), nullable=True))
    op.add_column('trainings', sa.Column('start_date', sa.DateTime(), nullable=True))
    op.add_column('trainings', sa.Column('end_date', sa.DateTime(), nullable=True))
    op.add_column('trainings', sa.Column('mandatory', sa.Boolean(), nullable=True, default=False))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns from trainings table
    op.drop_column('trainings', 'mandatory')
    op.drop_column('trainings', 'end_date')
    op.drop_column('trainings', 'start_date')
    op.drop_column('trainings', 'passing_score')
    op.drop_column('trainings', 'course_code')
