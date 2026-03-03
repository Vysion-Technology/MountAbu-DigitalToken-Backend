from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.database import Base


class ContactDiary(Base):
    __tablename__ = "contact_diaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    office_department: Mapped[str] = mapped_column(String, index=True)
    contact_person: Mapped[str] = mapped_column(String, index=True)
    designation: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    status: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    creator = relationship("User")
