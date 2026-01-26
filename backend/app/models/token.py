"""Token models: Token, TokenShare, VehicleEntry."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TokenShareStatus, TokenStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.core import User


class Token(Base, TimestampMixin):
    """E-Tokens for material transport."""

    __tablename__ = "tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    token_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Linked application
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False
    )

    # Linked to estimate phase (optional)
    estimate_phase_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estimate_phases.id"), nullable=True
    )

    # Phase
    phase_number: Mapped[int] = mapped_column(Integer, nullable=False)
    phase_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Materials (JSONB array)
    materials: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(Enum(TokenStatus), default=TokenStatus.PENDING)

    # Validity
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # QR
    qr_code_data: Mapped[str] = mapped_column(Text, nullable=False)

    # Usage
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Generation
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Cancellation
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="tokens"
    )
    vehicle_entries: Mapped[list["VehicleEntry"]] = relationship(
        "VehicleEntry", back_populates="token"
    )
    shares: Mapped[list["TokenShare"]] = relationship(
        "TokenShare", back_populates="token"
    )


class TokenShare(Base, TimestampMixin):
    """Token sharing with drivers for material transport."""

    __tablename__ = "token_shares"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    token_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False
    )

    # Shared by (applicant)
    shared_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Driver details
    driver_name: Mapped[str] = mapped_column(String(255), nullable=False)
    driver_mobile: Mapped[str] = mapped_column(String(15), nullable=False)
    vehicle_number: Mapped[str] = mapped_column(String(20), nullable=False)

    # Share link
    share_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    share_link: Mapped[str] = mapped_column(Text, nullable=False)

    # Material limits for this share
    material_limits: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Validity
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Status
    status: Mapped[str] = mapped_column(
        Enum(TokenShareStatus), default=TokenShareStatus.ACTIVE
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Notification status
    sms_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    whatsapp_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    token: Mapped["Token"] = relationship("Token", back_populates="shares")
    sharer: Mapped["User"] = relationship("User", foreign_keys=[shared_by])


class VehicleEntry(Base, TimestampMixin):
    """Vehicle entry logs at naka checkpoints."""

    __tablename__ = "vehicle_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Token
    token_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tokens.id"), nullable=False
    )
    token_share_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("token_shares.id"), nullable=True
    )

    # Vehicle
    vehicle_number: Mapped[str] = mapped_column(String(20), nullable=False)
    driver_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    driver_mobile: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)

    # Material
    material_type: Mapped[str] = mapped_column(String(50), nullable=False)
    material_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    # Location
    naka_location: Mapped[str] = mapped_column(String(100), nullable=False)
    naka_coordinates: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Verification
    verified_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Photos
    photos: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    token: Mapped["Token"] = relationship("Token", back_populates="vehicle_entries")
