"""add DELETED to AuditAction

Revision ID: d42b869e3ab1
Revises: 0ddbf653aea1
Create Date: 2026-05-04 18:26:02.856939

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd42b869e3ab1'
down_revision: Union[str, Sequence[str], None] = '0ddbf653aea1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'DELETED'")
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
