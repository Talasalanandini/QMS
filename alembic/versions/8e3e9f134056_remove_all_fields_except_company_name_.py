"""remove_all_fields_except_company_name_timezone_logo_url

Revision ID: 8e3e9f134056
Revises: 03af88e29153
Create Date: 2025-08-11 11:06:07.864136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e3e9f134056'
down_revision: Union[str, Sequence[str], None] = '03af88e29153'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove all fields except company_name, timezone, and logo_url
    # Only remove columns that we know exist from the original table
    op.drop_column('clients', 'industry')
    op.drop_column('clients', 'contact_email')
    op.drop_column('clients', 'contact_phone')


def downgrade() -> None:
    """Downgrade schema."""
    # Add back the removed columns
    op.add_column('clients', sa.Column('industry', sa.String(), nullable=False))
    op.add_column('clients', sa.Column('contact_email', sa.String(), nullable=False))
    op.add_column('clients', sa.Column('contact_phone', sa.String(), nullable=True))
