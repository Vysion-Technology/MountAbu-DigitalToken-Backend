"""create tenders table

Revision ID: f3g4h5i6j7k8
Revises: e2f3g4h5i6j7
Create Date: 2026-02-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f3g4h5i6j7k8'
down_revision = 'e2f3g4h5i6j7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tenders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('tender_type', sa.String(), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('published_on', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submission_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'EXPIRED', 'CANCELLED', 'CLOSED', name='tenderstatus'), nullable=False, server_default='ACTIVE'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_tenders_id'), 'tenders', ['id'], unique=False)
    op.create_index(op.f('ix_tenders_title'), 'tenders', ['title'], unique=False)
    op.create_index(op.f('ix_tenders_status'), 'tenders', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_tenders_status'), table_name='tenders')
    op.drop_index(op.f('ix_tenders_title'), table_name='tenders')
    op.drop_index(op.f('ix_tenders_id'), table_name='tenders')
    op.drop_table('tenders')
