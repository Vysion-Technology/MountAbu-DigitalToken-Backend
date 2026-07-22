from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from backend.meta import TenderStatus


class EventCreate(BaseModel):
    title: str = Field(..., description="Title of the event")
    event_type: Optional[str] = Field(None, description="Type/category of event")
    date: Optional[datetime] = Field(None, description="Date/time of event")
    venue: Optional[str] = Field(None, description="Venue of the event")
    description: Optional[str] = Field(None, description="Detailed description of the event")
    status: Optional[TenderStatus] = Field(TenderStatus.ACTIVE)


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None)
    event_type: Optional[str] = Field(None)
    date: Optional[datetime] = Field(None)
    venue: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    status: Optional[TenderStatus] = Field(None)
    image_path: Optional[str] = Field(None)
