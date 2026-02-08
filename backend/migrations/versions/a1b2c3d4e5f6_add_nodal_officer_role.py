"""add missing enum values (NODAL_OFFICER, doc types, statuses)

Revision ID: a1b2c3d4e5f6
Revises: c7910d98c1d4
Create Date: 2026-02-08 12:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic
revision = "a1b2c3d4e5f6"
down_revision = "c7910d98c1d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # UserRole
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'NODAL_OFFICER' AFTER 'SUPERADMIN'")

    # ApplicationDocumentType
    op.execute("ALTER TYPE applicationdocumenttype ADD VALUE IF NOT EXISTS 'AADHAAR'")
    op.execute("ALTER TYPE applicationdocumenttype ADD VALUE IF NOT EXISTS 'APPLICANT_PHOTO'")
    op.execute("ALTER TYPE applicationdocumenttype ADD VALUE IF NOT EXISTS 'OWNERSHIP_DOCUMENTS'")
    op.execute("ALTER TYPE applicationdocumenttype ADD VALUE IF NOT EXISTS 'PROPERTY_PHOTOS'")
    op.execute("ALTER TYPE applicationdocumenttype ADD VALUE IF NOT EXISTS 'SUPPORTING_DOCUMENTS'")

    # ApplicationStatus
    op.execute("ALTER TYPE applicationstatus ADD VALUE IF NOT EXISTS 'OBJECTED'")

    # ApplicationPhaseStatus
    op.execute("ALTER TYPE applicationphasestatus ADD VALUE IF NOT EXISTS 'WITHHELD'")
    op.execute("ALTER TYPE applicationphasestatus ADD VALUE IF NOT EXISTS 'TERMINATED'")


def downgrade() -> None:
    # Postgres does not support removing enum values; noop
    pass
