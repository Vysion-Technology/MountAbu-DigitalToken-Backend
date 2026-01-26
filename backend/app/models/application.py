"""Application models: Application, ApplicationTimeline, Document."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ApplicationStatus, ApplicationType
from app.models.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.core import User
    from app.models.token import Token


class Application(Base, TimestampMixin, SoftDeleteMixin):
    """Construction/renovation applications."""

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Type
    application_type: Mapped[str] = mapped_column(Enum(ApplicationType), nullable=False)

    # Applicant
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Details (JSONB for flexibility)
    property_details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    construction_details: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        Enum(ApplicationStatus), default=ApplicationStatus.SUBMITTED
    )
    current_authority_role: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    current_authority_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Processing timestamps
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_action_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Approval/Rejection
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    approval_conditions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Permission document
    permission_document_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Terms
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    declaration_accepted: Mapped[bool] = mapped_column(Boolean, default=False)

    # SLA
    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    applicant: Mapped["User"] = relationship(
        "User", back_populates="applications", foreign_keys=[applicant_id]
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="application", cascade="all, delete-orphan"
    )
    tokens: Mapped[list["Token"]] = relationship(
        "Token", back_populates="application", cascade="all, delete-orphan"
    )
    timeline: Mapped[list["ApplicationTimeline"]] = relationship(
        "ApplicationTimeline",
        back_populates="application",
        cascade="all, delete-orphan",
    )


class ApplicationTimeline(Base):
    """Application workflow timeline/history."""

    __tablename__ = "application_timeline"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False
    )

    # Event
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)

    # Actor
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    actor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Details
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="timeline")


class Document(Base, TimestampMixin, SoftDeleteMixin):
    """Uploaded documents for applications."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False
    )

    # Document info
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)

    # Verification
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Upload info
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="documents")
