"""create notices table

Revision ID: e2f3g4h5i6j7
Revises: d1a2b3c4d5e6
Create Date: 2026-02-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e2f3g4h5i6j7'
down_revision = 'd1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'notices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('notice_type', sa.String(), nullable=True),
        sa.Column('published_on', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_till', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'EXPIRED', 'INACTIVE', name='noticestatus'), nullable=False, server_default='ACTIVE'),
        sa.Column('visibility', sa.Enum('PUBLIC', 'INTERNAL', name='noticevisibility'), nullable=False, server_default='PUBLIC'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_notices_id'), 'notices', ['id'], unique=False)
    op.create_index(op.f('ix_notices_status'), 'notices', ['status'], unique=False)
    op.create_index(op.f('ix_notices_visibility'), 'notices', ['visibility'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_notices_visibility'), table_name='notices')
    op.drop_index(op.f('ix_notices_status'), table_name='notices')
    op.drop_index(op.f('ix_notices_id'), table_name='notices')
    op.drop_table('notices')
