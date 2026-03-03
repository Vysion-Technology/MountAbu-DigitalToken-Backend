from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ContactDiaryResponse(BaseModel):
    id: int
    office_department: str
    contact_person: str
    designation: Optional[str] = None
    phone_number: Optional[str] = None
    email_address: Optional[str] = None
    status: bool

    created_by: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedContactDiaryResponse(BaseModel):
    items: List[ContactDiaryResponse]
    total: int
    page: int
    size: int
    pages: int
