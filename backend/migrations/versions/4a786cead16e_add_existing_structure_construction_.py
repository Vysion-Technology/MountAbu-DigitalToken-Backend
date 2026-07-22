"""add_existing_structure_construction_floor_jurisdiction_zone

Revision ID: 4a786cead16e
Revises: 3bca75a636e3
Create Date: 2026-07-02 15:27:27.232011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a786cead16e'
down_revision: Union[str, Sequence[str], None] = '3bca75a636e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum types
    structure_type = sa.Enum('NONE', 'FENCING', 'G', 'G_1', 'G_2', 'G_3', name='structuretype')
    structure_type.create(op.get_bind(), checkfirst=True)
    
    jurisdiction_zone = sa.Enum('ULB', 'UIT', name='jurisdictionzone')
    jurisdiction_zone.create(op.get_bind(), checkfirst=True)
    
    op.add_column('applications', sa.Column('existing_structure', structure_type, nullable=True))
    op.add_column('applications', sa.Column('construction_floor', structure_type, nullable=True))
    op.add_column('applications', sa.Column('jurisdiction_zone', jurisdiction_zone, nullable=True))
    
    # Update existing data to default 'ULB'
    op.execute("UPDATE applications SET jurisdiction_zone = 'ULB'")
    
    # Make jurisdiction_zone NOT NULL
    op.alter_column('applications', 'jurisdiction_zone', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('applications', 'jurisdiction_zone')
    op.drop_column('applications', 'construction_floor')
    op.drop_column('applications', 'existing_structure')
    
    # Drop enum types
    sa.Enum(name='structuretype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='jurisdictionzone').drop(op.get_bind(), checkfirst=True)
