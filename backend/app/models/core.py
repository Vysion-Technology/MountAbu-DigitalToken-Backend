"""Core models: Role, User, Permission, Session."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PermissionCategory, RoleType, UserStatus, UserType
from app.models.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.blacklist import UserBlacklistStatus
    from app.models.application import Application


class Role(Base, TimestampMixin):
    """Authority roles table."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Enum(RoleType), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hierarchy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    can_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    can_reject: Mapped[bool] = mapped_column(Boolean, default=False)
    can_forward: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="role")
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary="role_permissions", back_populates="roles"
    )


class User(Base, TimestampMixin, SoftDeleteMixin):
    """Users table - both applicants and authorities."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic info
    user_type: Mapped[str] = mapped_column(Enum(UserType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Aadhaar (encrypted)
    aadhaar_number_encrypted: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    aadhaar_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    aadhaar_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    aadhaar_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(100), default="Rajasthan")
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Authority-specific
    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True
    )
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    mobile_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Language
    preferred_language: Mapped[str] = mapped_column(String(5), default="en")

    # Login tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    login_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    role: Mapped[Optional["Role"]] = relationship("Role", back_populates="users")
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="applicant",
        foreign_keys="Application.applicant_id",
    )
    blacklist_status: Mapped[Optional["UserBlacklistStatus"]] = relationship(
        "UserBlacklistStatus",
        back_populates="user",
        uselist=False,
        foreign_keys="UserBlacklistStatus.user_id",
    )

    __table_args__ = (
        UniqueConstraint("mobile", name="uq_users_mobile"),
        UniqueConstraint("email", name="uq_users_email"),
    )


class Permission(Base, TimestampMixin):
    """Granular permissions for RBAC."""

    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(Enum(PermissionCategory), nullable=False)

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="role_permissions", back_populates="permissions"
    )


class RolePermission(Base):
    """Many-to-many relationship between roles and permissions."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Session(Base, TimestampMixin):
    """User session management with JWT tokens."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Token info (hashed for security)
    access_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Session details
    device_info: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Expiry
    access_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    refresh_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", backref="sessions")


class OTPSession(Base, TimestampMixin):
    """OTP sessions for login verification."""

    __tablename__ = "otp_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False)  # mobile or email
    user_type: Mapped[str] = mapped_column(Enum(UserType), nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
