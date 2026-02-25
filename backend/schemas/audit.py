from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel
from backend.meta.audit import AuditAction


class AuditLogBase(BaseModel):
    entity_type: str
    action: AuditAction
    user_id: int
    previous_state: Optional[Any] = None
    new_state: Optional[Any] = None


class AuditLogResponse(AuditLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    total: int
    logs: List[AuditLogResponse]
