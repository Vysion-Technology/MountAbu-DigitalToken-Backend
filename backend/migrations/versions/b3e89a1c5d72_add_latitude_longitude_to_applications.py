"""add_latitude_longitude_to_applications

Revision ID: b3e89a1c5d72
Revises: e57b91c34a21
Create Date: 2026-10-18 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e89a1c5d72'
down_revision: Union[str, Sequence[str], None] = 'e57b91c34a21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'applications',
        sa.Column('latitude', sa.Float(), nullable=True)
    )
    op.add_column(
        'applications',
        sa.Column('longitude', sa.Float(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('applications', 'longitude')
    op.drop_column('applications', 'latitude')
