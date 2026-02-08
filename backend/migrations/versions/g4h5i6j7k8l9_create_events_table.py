"""create events table

Revision ID: g4h5i6j7k8l9
Revises: f3g4h5i6j7k8
Create Date: 2026-02-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'g4h5i6j7k8l9'
down_revision = 'f3g4h5i6j7k8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('venue', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'EXPIRED', 'CANCELLED', 'CLOSED', name='eventstatus'), nullable=False, server_default='ACTIVE'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_events_id'), 'events', ['id'], unique=False)
    op.create_index(op.f('ix_events_title'), 'events', ['title'], unique=False)
    op.create_index(op.f('ix_events_status'), 'events', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_events_status'), table_name='events')
    op.drop_index(op.f('ix_events_title'), table_name='events')
    op.drop_index(op.f('ix_events_id'), table_name='events')
    op.drop_table('events')
