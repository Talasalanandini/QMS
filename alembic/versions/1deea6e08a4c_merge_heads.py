"""merge_heads

Revision ID: 1deea6e08a4c
Revises: add_missing_audit_fields, workorder_001
Create Date: 2025-08-06 10:55:35.652535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1deea6e08a4c'
down_revision: Union[str, Sequence[str], None] = ('add_missing_audit_fields', 'workorder_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
