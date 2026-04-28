from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from backend.meta import NoticeStatus


class LeaderCreate(BaseModel):
    name: str = Field(..., description="Leader name")
    designation: Optional[str] = Field(None, description="Designation / title")
    tenure_start: Optional[datetime] = Field(None)
    tenure_end: Optional[datetime] = Field(None)
    status: Optional[NoticeStatus] = Field(NoticeStatus.ACTIVE)


class LeaderUpdate(BaseModel):
    name: Optional[str] = Field(None)
    designation: Optional[str] = Field(None)
    tenure_start: Optional[datetime] = Field(None)
    tenure_end: Optional[datetime] = Field(None)
    status: Optional[NoticeStatus] = Field(None)
    image_path: Optional[str] = Field(None)
