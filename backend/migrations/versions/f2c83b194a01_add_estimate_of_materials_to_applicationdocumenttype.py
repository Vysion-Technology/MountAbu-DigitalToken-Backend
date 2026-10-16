"""add_estimate_of_materials_to_applicationdocumenttype

Revision ID: f2c83b194a01
Revises: a93b350af71c
Create Date: 2026-10-16 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2c83b194a01'
down_revision: Union[str, Sequence[str], None] = 'a93b350af71c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("ALTER TYPE applicationdocumenttype ADD VALUE IF NOT EXISTS 'ESTIMATE_OF_MATERIALS'"))


def downgrade() -> None:
    """Downgrade schema."""
    pass
