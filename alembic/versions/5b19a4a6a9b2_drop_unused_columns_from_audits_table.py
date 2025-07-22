"""drop unused columns from audits table

Revision ID: 5b19a4a6a9b2
Revises: eb92eb007aea
Create Date: 2025-07-21 15:18:05.102516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b19a4a6a9b2'
down_revision: Union[str, Sequence[str], None] = 'eb92eb007aea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('audits', 'audit_code')
    op.drop_column('audits', 'description')
    op.drop_column('audits', 'department_id')
    op.drop_column('audits', 'start_date')
    op.drop_column('audits', 'end_date')
    op.drop_column('audits', 'created_at')
    op.drop_column('audits', 'updated_at')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('audits', sa.Column('audit_code', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('audits', sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('audits', sa.Column('department_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('audits', sa.Column('start_date', sa.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('audits', sa.Column('end_date', sa.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('audits', sa.Column('created_at', sa.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('audits', sa.Column('updated_at', sa.TIMESTAMP(), autoincrement=False, nullable=True))
