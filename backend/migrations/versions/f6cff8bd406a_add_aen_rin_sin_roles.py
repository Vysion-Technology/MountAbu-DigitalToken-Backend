"""add_aen_rin_sin_roles

Revision ID: f6cff8bd406a
Revises: 24a013257855
Create Date: 2026-05-21 11:39:11.361309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6cff8bd406a'
down_revision: Union[str, Sequence[str], None] = '24a013257855'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'AEN'"))
    op.execute(sa.text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'RIN'"))
    op.execute(sa.text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SIN'"))


def downgrade() -> None:
    """Downgrade schema."""
    pass
