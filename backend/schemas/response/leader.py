from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from backend.meta import NoticeStatus


class LeaderResponse(BaseModel):
    id: int
    name: str
    designation: Optional[str]
    tenure_start: Optional[datetime]
    tenure_end: Optional[datetime]
    status: NoticeStatus
    created_by: Optional[int]
    created_at: Optional[datetime] = None


class LeadersListResponse(BaseModel):
    leaders: list[LeaderResponse] = []
    total: Optional[int]
