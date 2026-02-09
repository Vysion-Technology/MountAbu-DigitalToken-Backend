from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from backend.meta import NoticeStatus


class LeaderResponse(BaseModel):
    id: int
    name: str
    designation: Optional[str]
    tenure_start: Optional[datetime]
    tenure_end: Optional[datetime]
    status: NoticeStatus
    created_by: Optional[int]
    created_at: datetime


class LeadersListResponse(BaseModel):
    leaders: list[LeaderResponse] = []
    total: Optional[int]
