"""add_document_views_table

Revision ID: 47ac1453790b
Revises: c356ec63d55d
Create Date: 2025-08-08 18:27:47.872893

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47ac1453790b'
down_revision: Union[str, Sequence[str], None] = 'c356ec63d55d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
