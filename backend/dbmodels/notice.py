from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.database import Base
from backend.meta import NoticeStatus, Visibility


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String, index=True)
    notice_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    published_on: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_till: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[NoticeStatus] = mapped_column(SAEnum(NoticeStatus, name='noticestatus'), default=NoticeStatus.ACTIVE, index=True)
    visibility: Mapped[Visibility] = mapped_column(SAEnum(Visibility, name='noticevisibility'), default=Visibility.PUBLIC, index=True)

    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User")
