from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from backend.dbmodels.user import User

from backend.database import Base


class Ward(Base):
    __tablename__ = "wards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    code: Mapped[str] = mapped_column(String, index=True, unique=True)
    type: Mapped[str] = mapped_column(String, default="Ward")  # Ward or Zone
    description: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, default=1
    )

    created_by: Mapped["User"] = relationship("User")


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    code: Mapped[str] = mapped_column(String, index=True, unique=True)
    type: Mapped[str] = mapped_column(String)  # Municipal, Planning, etc.
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    jen_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, default=1
    )

    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
    jen: Mapped["User"] = relationship("User", foreign_keys=[jen_id])


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    code: Mapped[str] = mapped_column(String, index=True, unique=True)
    permissions: Mapped[str] = mapped_column(
        String, nullable=True
    )  # JSON or CSV of permissions
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, default=1
    )

    created_by: Mapped["User"] = relationship("User")


class ComplaintCategory(Base):
    __tablename__ = "complaint_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id"), nullable=True
    )
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, default=1
    )

    created_by: Mapped["User"] = relationship("User")
    department = relationship("Department")
