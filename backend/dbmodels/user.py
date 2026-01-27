from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import mapped_column, Mapped

from backend.database import Base
from backend.meta import UserRole


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), index=True, default=UserRole.CITIZEN
    )
    name: Mapped[str] = mapped_column(String, index=True)
    mobile: Mapped[str] = mapped_column(
        String, index=True, min_length=10, max_length=10
    )
