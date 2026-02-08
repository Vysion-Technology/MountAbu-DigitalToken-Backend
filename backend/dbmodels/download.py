from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.database import Base
from backend.meta import DownloadStatus


class Download(Base):
    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    document_title: Mapped[str] = mapped_column(String, index=True)
    document_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True, index=True)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    file_path: Mapped[str] = mapped_column(String, nullable=False)  # S3 key / object path
    status: Mapped[DownloadStatus] = mapped_column(SAEnum(DownloadStatus, name='downloadstatus'), default=DownloadStatus.ACTIVE, index=True)  # ACTIVE / INACTIVE

    uploaded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    uploaded_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    department = relationship("Department")
    uploader = relationship("User")
