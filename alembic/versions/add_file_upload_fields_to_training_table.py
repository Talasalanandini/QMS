"""add_file_upload_fields_to_training_table

Revision ID: add_file_upload_fields_to_training_table
Revises: 1deea6e08a4c
Create Date: 2025-08-06 10:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_file_upload_fields_to_training_table'
down_revision: Union[str, Sequence[str], None] = '1deea6e08a4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add file upload fields to trainings table
    op.add_column('trainings', sa.Column('content_type', sa.String(), nullable=True))
    op.add_column('trainings', sa.Column('file_path', sa.String(), nullable=True))
    op.add_column('trainings', sa.Column('file_name', sa.String(), nullable=True))
    op.add_column('trainings', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('trainings', sa.Column('file_type', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove file upload fields from trainings table
    op.drop_column('trainings', 'file_type')
    op.drop_column('trainings', 'file_size')
    op.drop_column('trainings', 'file_name')
    op.drop_column('trainings', 'file_path')
    op.drop_column('trainings', 'content_type') 