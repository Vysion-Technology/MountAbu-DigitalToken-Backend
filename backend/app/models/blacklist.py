"""Blacklist and Audit models."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import BlacklistAction
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.core import User


class UserBlacklistStatus(Base, TimestampMixin):
    """Tracks user blacklist status for fraud prevention."""

    __tablename__ = "user_blacklist_status"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )

    # Status
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Counters
    consecutive_rejections: Mapped[int] = mapped_column(Integer, default=0)
    total_rejections: Mapped[int] = mapped_column(Integer, default=0)
    total_approvals: Mapped[int] = mapped_column(Integer, default=0)

    # Blacklist info
    blacklisted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    blacklist_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blacklist_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    blacklisted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Last rejection
    last_rejection_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_rejection_application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Whitelist info
    whitelisted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    whitelisted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    whitelist_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Warning
    warning_issued: Mapped[bool] = mapped_column(Boolean, default=False)
    warning_issued_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="blacklist_status", foreign_keys=[user_id]
    )


class ApplicationRejection(Base):
    """Detailed rejection history for blacklist tracking."""

    __tablename__ = "application_rejections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False
    )

    # Rejection details
    rejected_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    rejected_by_role: Mapped[str] = mapped_column(String(50), nullable=False)
    rejection_reason: Mapped[str] = mapped_column(String(100), nullable=False)
    rejection_category: Mapped[str] = mapped_column(String(50), nullable=False)
    authority_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Consecutive tracking
    was_consecutive: Mapped[bool] = mapped_column(Boolean, default=True)
    consecutive_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    triggered_blacklist: Mapped[bool] = mapped_column(Boolean, default=False)

    rejected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class BlacklistAuditLog(Base):
    """Audit log specifically for blacklist/whitelist actions."""

    __tablename__ = "blacklist_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Action
    action: Mapped[str] = mapped_column(Enum(BlacklistAction), nullable=False)
    performed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    # Additional metadata
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AuditLog(Base):
    """General audit log for all actions."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Actor
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    user_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Action
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Details
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Changes
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
