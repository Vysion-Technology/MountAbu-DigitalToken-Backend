from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from backend.meta import NoticeStatus, Visibility


class NoticeCreate(BaseModel):
    title: str = Field(..., description="Title of the notice")
    notice_type: Optional[str] = Field(None, description="Type/category of notice")
    published_on: Optional[datetime] = Field(None, description="When it was published")
    valid_till: Optional[datetime] = Field(None, description="Valid until date/time")
    status: Optional[NoticeStatus] = Field(NoticeStatus.ACTIVE, description="Status - ACTIVE/EXPIRED/INACTIVE")
    visibility: Optional[Visibility] = Field(Visibility.PUBLIC, description="Visibility - PUBLIC/INTERNAL")
    content: Optional[str] = Field(None, description="Content/body of the notice")


class NoticeUpdate(BaseModel):
    title: Optional[str] = Field(None)
    notice_type: Optional[str] = Field(None)
    published_on: Optional[datetime] = Field(None)
    valid_till: Optional[datetime] = Field(None)
    status: Optional[NoticeStatus] = Field(None)
    visibility: Optional[Visibility] = Field(None)
    image_path: Optional[str] = Field(None)
    document_path: Optional[str] = Field(None)
    content: Optional[str] = Field(None)
