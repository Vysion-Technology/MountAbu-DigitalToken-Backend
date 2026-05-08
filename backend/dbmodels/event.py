from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.database import Base
from backend.meta import TenderStatus


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String, index=True)
    event_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    status: Mapped[TenderStatus] = mapped_column(SAEnum(TenderStatus, name="eventstatus"), default=TenderStatus.ACTIVE, index=True)

    image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User")
