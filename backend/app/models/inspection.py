"""Inspection models: Inspection, InspectionPhoto."""

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
from app.models.enums import InspectionRecommendation, InspectionStatus, InspectionType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.core import User


class Inspection(Base, TimestampMixin):
    """Site inspection records by JEN."""

    __tablename__ = "inspections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Inspection type
    inspection_type: Mapped[str] = mapped_column(Enum(InspectionType), nullable=False)

    # Inspector
    inspector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Inspection details
    inspection_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Findings (flexible JSONB)
    findings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Recommendation
    recommendation: Mapped[Optional[str]] = mapped_column(
        Enum(InspectionRecommendation), nullable=True
    )
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Layout approval (for JEN)
    layout_approved: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    layout_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        Enum(InspectionStatus), default=InspectionStatus.PENDING
    )

    # Location verification
    inspection_location: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", backref="inspections"
    )
    inspector: Mapped["User"] = relationship("User", foreign_keys=[inspector_id])
    photos: Mapped[list["InspectionPhoto"]] = relationship(
        "InspectionPhoto", back_populates="inspection", cascade="all, delete-orphan"
    )


class InspectionPhoto(Base, TimestampMixin):
    """Geo-tagged photos from site inspections."""

    __tablename__ = "inspection_photos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Photo info
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    public_url: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Geo-tag (required)
    latitude: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    altitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    accuracy: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    # Verification
    geo_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    within_property_bounds: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )

    # Capture info
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    device_info: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    inspection: Mapped["Inspection"] = relationship(
        "Inspection", back_populates="photos"
    )
