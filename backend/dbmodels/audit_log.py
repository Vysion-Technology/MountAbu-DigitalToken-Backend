from datetime import datetime
from sqlalchemy import Integer, String, DateTime, JSON, Enum
from sqlalchemy.orm import mapped_column, Mapped

from backend.database import Base
from backend.meta.audit import AuditAction


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    previous_state: Mapped[dict] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
