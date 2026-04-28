from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from backend.meta import TenderStatus


class EventResponse(BaseModel):
    id: int
    title: str
    event_type: Optional[str]
    date: Optional[datetime]
    venue: Optional[str]
    status: TenderStatus
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    created_by: Optional[int]
    created_at: Optional[datetime] = None


class EventsListResponse(BaseModel):
    events: list[EventResponse] = []
    total: Optional[int]
