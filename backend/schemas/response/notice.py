from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from backend.meta import NoticeStatus, Visibility


class NoticeResponse(BaseModel):
    id: int
    title: str
    notice_type: Optional[str]
    published_on: Optional[datetime]
    valid_till: Optional[datetime]
    status: NoticeStatus
    visibility: Visibility
    created_by: Optional[int]
    created_at: Optional[datetime] = None


class NoticesListResponse(BaseModel):
    notices: list[NoticeResponse] = []
    total: Optional[int]
