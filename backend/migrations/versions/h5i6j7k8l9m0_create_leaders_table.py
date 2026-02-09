"""create leaders table

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2026-02-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h5i6j7k8l9m0'
down_revision = 'g4h5i6j7k8l9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'leaders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('designation', sa.String(), nullable=True),
        sa.Column('tenure_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tenure_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'EXPIRED', 'INACTIVE', name='leaderstatus'), nullable=False, server_default='ACTIVE'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_leaders_id'), 'leaders', ['id'], unique=False)
    op.create_index(op.f('ix_leaders_name'), 'leaders', ['name'], unique=False)
    op.create_index(op.f('ix_leaders_status'), 'leaders', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_leaders_status'), table_name='leaders')
    op.drop_index(op.f('ix_leaders_name'), table_name='leaders')
    op.drop_index(op.f('ix_leaders_id'), table_name='leaders')
    op.drop_table('leaders')
