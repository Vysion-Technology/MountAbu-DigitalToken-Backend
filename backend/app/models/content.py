"""Content Management models: Page, Notice, Tender."""

import uuid
from datetime import datetime
from typing import Optional

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ContentStatus
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class Page(Base, TimestampMixin):
    """Website CMS pages."""

    __tablename__ = "pages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    title_hi: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Hindi

    # Content (HTML/Markdown)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Hindi

    # Meta
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_keywords: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        Enum(ContentStatus), default=ContentStatus.DRAFT
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Author
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class Notice(Base, TimestampMixin, SoftDeleteMixin):
    """Public notices and announcements."""

    __tablename__ = "notices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_hi: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Attachment
    attachment_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachment_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Display settings
    is_important: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    # Validity
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        Enum(ContentStatus), default=ContentStatus.DRAFT
    )

    # Author
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )


class Tender(Base, TimestampMixin, SoftDeleteMixin):
    """Tender postings."""

    __tablename__ = "tenders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tender_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_hi: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Description
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_hi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Documents
    document_url: Mapped[str] = mapped_column(Text, nullable=False)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Dates
    published_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submission_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    opening_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Value
    estimated_value: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        Enum(ContentStatus), default=ContentStatus.DRAFT
    )

    # Author
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
