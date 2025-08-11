"""add_base64_column_to_documents

Revision ID: b042b2586350
Revises: a3fd0fd428c7
Create Date: 2025-08-08 11:43:36.947266

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b042b2586350'
down_revision: Union[str, Sequence[str], None] = 'a3fd0fd428c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add file_base64 column to documents table
    op.add_column('documents', sa.Column('file_base64', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove file_base64 column from documents table
    op.drop_column('documents', 'file_base64')
