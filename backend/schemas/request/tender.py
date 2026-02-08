from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from backend.meta import TenderStatus


class TenderCreate(BaseModel):
    title: str = Field(..., description="Title of the tender")
    tender_type: Optional[str] = Field(None, description="Type/category of tender")
    department_id: Optional[int] = Field(None, description="Department id")
    amount: Optional[float] = Field(None, description="Tender amount")
    published_on: Optional[datetime] = Field(None)
    submission_deadline: Optional[datetime] = Field(None)
    status: Optional[TenderStatus] = Field(TenderStatus.ACTIVE)


class TenderUpdate(BaseModel):
    title: Optional[str] = Field(None)
    tender_type: Optional[str] = Field(None)
    department_id: Optional[int] = Field(None)
    amount: Optional[float] = Field(None)
    published_on: Optional[datetime] = Field(None)
    submission_deadline: Optional[datetime] = Field(None)
    status: Optional[TenderStatus] = Field(None)
