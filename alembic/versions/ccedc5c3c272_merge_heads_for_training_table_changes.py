"""merge heads for training table changes

Revision ID: ccedc5c3c272
Revises: add_file_upload_fields_to_training_table, add_training_assignments_table
Create Date: 2025-08-06 12:01:51.419396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccedc5c3c272'
down_revision: Union[str, Sequence[str], None] = ('add_file_upload_fields_to_training_table', 'add_training_assignments_table')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
