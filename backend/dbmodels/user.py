from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy import Enum, Integer, String, DateTime
from sqlalchemy.orm import mapped_column, Mapped

from backend.database import Base
from backend.meta import UserRole, JurisdictionZone


class ActiveUserOTP(Base):
    __tablename__ = "active_user_otps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mobile: Mapped[str] = mapped_column(String, index=True)
    otp: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    valid_till: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now() + timedelta(minutes=5)
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), index=True, default=UserRole.CITIZEN
    )
    name: Mapped[str] = mapped_column(String, index=True)
    mobile: Mapped[str] = mapped_column(String(10), index=True)
    username: Mapped[Optional[str]] = mapped_column(String, index=True)
    password: Mapped[Optional[str]] = mapped_column(String, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    jurisdiction_zone: Mapped[Optional[JurisdictionZone]] = mapped_column(
        Enum(JurisdictionZone), nullable=True
    )
