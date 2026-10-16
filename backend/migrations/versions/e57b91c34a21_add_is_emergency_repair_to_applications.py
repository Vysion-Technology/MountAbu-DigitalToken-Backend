"""add_is_emergency_repair_to_applications

Revision ID: e57b91c34a21
Revises: f2c83b194a01
Create Date: 2026-10-16 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e57b91c34a21'
down_revision: Union[str, Sequence[str], None] = 'f2c83b194a01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'applications',
        sa.Column('is_emergency_repair', sa.Boolean(), server_default=sa.text('false'), nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('applications', 'is_emergency_repair')
