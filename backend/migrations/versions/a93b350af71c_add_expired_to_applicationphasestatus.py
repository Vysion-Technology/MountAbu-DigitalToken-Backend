"""add_expired_to_applicationphasestatus

Revision ID: 1f1827214884
Revises: d0edb72e89e6
Create Date: 2026-10-11 16:07:29.664675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a93b350af71c'
down_revision: Union[str, Sequence[str], None] = 'd0edb72e89e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("ALTER TYPE applicationphasestatus ADD VALUE IF NOT EXISTS 'EXPIRED'"))


def downgrade() -> None:
    """Downgrade schema."""
    pass
