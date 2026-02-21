from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from backend.meta import TenderStatus


class TenderResponse(BaseModel):
    id: int
    title: str
    tender_type: Optional[str]
    department_id: Optional[int]
    amount: Optional[float]
    published_on: Optional[datetime]
    submission_deadline: Optional[datetime]
    status: TenderStatus
    created_by: Optional[int]
    created_at: Optional[datetime] = None


class TendersListResponse(BaseModel):
    tenders: list[TenderResponse] = []
    total: Optional[int]
