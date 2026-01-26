"""Estimate models: Estimate, EstimatePhase."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
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
from app.models.enums import EstimatePhaseStatus, EstimateStatus, EstimateType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.token import Token


class Estimate(Base, TimestampMixin):
    """Material estimates for applications."""

    __tablename__ = "estimates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Estimate type
    estimate_type: Mapped[str] = mapped_column(Enum(EstimateType), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Source file
    source_file_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Total materials (denormalized for quick access)
    total_materials: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        Enum(EstimateStatus), default=EstimateStatus.PENDING
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Upload info
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", backref="estimates"
    )
    phases: Mapped[list["EstimatePhase"]] = relationship(
        "EstimatePhase", back_populates="estimate", cascade="all, delete-orphan"
    )


class EstimatePhase(Base, TimestampMixin):
    """Phase-wise breakdown of material estimates."""

    __tablename__ = "estimate_phases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    estimate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("estimates.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Phase info
    phase_number: Mapped[int] = mapped_column(Integer, nullable=False)
    phase_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Materials for this phase (JSON array)
    materials: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        Enum(EstimatePhaseStatus), default=EstimatePhaseStatus.PENDING
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    estimate: Mapped["Estimate"] = relationship("Estimate", back_populates="phases")
    tokens: Mapped[list["Token"]] = relationship("Token", backref="estimate_phase")

    __table_args__ = (
        UniqueConstraint("estimate_id", "phase_number", name="uq_estimate_phase"),
    )
