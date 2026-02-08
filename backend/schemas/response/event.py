from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from backend.meta import TenderStatus


class EventResponse(BaseModel):
    id: int
    title: str
    event_type: Optional[str]
    date: Optional[datetime]
    venue: Optional[str]
    status: TenderStatus
    created_by: Optional[int]
    created_at: datetime


class EventsListResponse(BaseModel):
    events: list[EventResponse] = []
    total: Optional[int]
