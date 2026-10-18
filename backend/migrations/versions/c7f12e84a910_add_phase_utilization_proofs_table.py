"""add_phase_utilization_proofs_table

Revision ID: c7f12e84a910
Revises: b3e89a1c5d72
Create Date: 2026-10-18 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f12e84a910'
down_revision: Union[str, Sequence[str], None] = 'b3e89a1c5d72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'phase_utilization_proofs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('phase', sa.Integer(), nullable=False),
        sa.Column('work_completion_details', sa.String(), nullable=False),
        sa.Column('completion_percentage', sa.Integer(), nullable=True),
        sa.Column('declaration_accepted', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('remarks', sa.String(), nullable=True),
        sa.Column('photos', sa.JSON(), nullable=True),
        sa.Column('submitted_by_id', sa.Integer(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.ForeignKeyConstraint(['submitted_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_phase_utilization_proofs_id'), 'phase_utilization_proofs', ['id'], unique=False)
    op.create_index(op.f('ix_phase_utilization_proofs_application_id'), 'phase_utilization_proofs', ['application_id'], unique=False)
    op.create_index(op.f('ix_phase_utilization_proofs_phase'), 'phase_utilization_proofs', ['phase'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_phase_utilization_proofs_phase'), table_name='phase_utilization_proofs')
    op.drop_index(op.f('ix_phase_utilization_proofs_application_id'), table_name='phase_utilization_proofs')
    op.drop_index(op.f('ix_phase_utilization_proofs_id'), table_name='phase_utilization_proofs')
    op.drop_table('phase_utilization_proofs')
