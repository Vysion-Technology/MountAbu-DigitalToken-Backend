from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.database import Base
from backend.meta import NoticeStatus


class Leader(Base):
    __tablename__ = "leaders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String, index=True)
    designation: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    tenure_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tenure_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[NoticeStatus] = mapped_column(SAEnum(NoticeStatus, name='leaderstatus'), default=NoticeStatus.ACTIVE, index=True)

    image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User")
