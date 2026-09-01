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


class SlotDefinition(Base):
    __tablename__ = "slot_definitions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    start_time: Mapped[str] = mapped_column(String)  # e.g., "08:00"
    end_time: Mapped[str] = mapped_column(String)    # e.g., "10:00"
    max_capacity: Mapped[int] = mapped_column(Integer, default=20)
    applicable_days: Mapped[str] = mapped_column(
        String, default="MON,TUE,WED,THU,FRI,SAT,SUN", server_default="MON,TUE,WED,THU,FRI,SAT,SUN"
    )
    grace_period_minutes: Mapped[int] = mapped_column(
        Integer, default=30, server_default="30"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, default=1
    )

    created_by: Mapped["User"] = relationship("User")


class VehicleType(Base):
    __tablename__ = "vehicle_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)  # e.g., "Pickup (4 Wheeler)"
    code: Mapped[str] = mapped_column(String, index=True, unique=True)  # e.g., "PICKUP_4W"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, default=1
    )

    created_by: Mapped["User"] = relationship("User")


class ScheduleBlackout(Base):
    __tablename__ = "schedule_blackouts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    blackout_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    reason: Mapped[str] = mapped_column(String)  # e.g., "Mount Abu Summer Festival"
    is_full_day: Mapped[bool] = mapped_column(Boolean, default=True)
    slot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("slot_definitions.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, default=1
    )

    slot = relationship("SlotDefinition")
    created_by: Mapped["User"] = relationship("User")


