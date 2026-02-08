"""create downloads table

Revision ID: d1a2b3c4d5e6
Revises: 
Create Date: 2026-02-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd1a2b3c4d5e6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'downloads',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('document_title', sa.String(), nullable=False),
        sa.Column('document_type', sa.String(), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', name='downloadstatus'), nullable=False, server_default='ACTIVE'),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('uploaded_on', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_downloads_id'), 'downloads', ['id'], unique=False)
    op.create_index(op.f('ix_downloads_document_type'), 'downloads', ['document_type'], unique=False)
    op.create_index(op.f('ix_downloads_status'), 'downloads', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_downloads_status'), table_name='downloads')
    op.drop_index(op.f('ix_downloads_document_type'), table_name='downloads')
    op.drop_index(op.f('ix_downloads_id'), table_name='downloads')
    op.drop_table('downloads')
