from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, DateTime, Numeric, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.database import Base
from backend.meta import TenderStatus


class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String, index=True)
    tender_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True, index=True)

    amount: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)

    published_on: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[TenderStatus] = mapped_column(SAEnum(TenderStatus, name='tenderstatus'), default=TenderStatus.ACTIVE, index=True)

    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    department = relationship("Department")
    creator = relationship("User")
