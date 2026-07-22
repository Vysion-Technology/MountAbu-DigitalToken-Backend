"""add_collector_user_role

Revision ID: a1b2c3d4e5f6
Revises: bab3282aa849
Create Date: 2026-07-18 11:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'bab3282aa849'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'COLLECTOR'"))


def downgrade() -> None:
    """Downgrade schema."""
    pass
