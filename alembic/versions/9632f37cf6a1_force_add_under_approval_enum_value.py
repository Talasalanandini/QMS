"""force_add_under_approval_enum_value

Revision ID: 9632f37cf6a1
Revises: f62b1e6eb486
Create Date: 2025-07-28 16:42:12.885432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9632f37cf6a1'
down_revision: Union[str, Sequence[str], None] = 'f62b1e6eb486'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Force add 'under_approval' to the documentstatusenum
    try:
        op.execute("ALTER TYPE documentstatusenum ADD VALUE 'under_approval'")
        print("Successfully added 'under_approval' to documentstatusenum")
    except Exception as e:
        print(f"Note: 'under_approval' might already exist in enum: {e}")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL doesn't support removing enum values
    pass
