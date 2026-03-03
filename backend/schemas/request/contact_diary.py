from typing import Optional
from pydantic import BaseModel, Field


class ContactDiaryCreate(BaseModel):
    office_department: str = Field(..., max_length=255)
    contact_person: str = Field(..., max_length=255)
    designation: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=50)
    email_address: Optional[str] = Field(None, max_length=255)
    status: Optional[bool] = Field(True)


class ContactDiaryUpdate(BaseModel):
    office_department: Optional[str] = Field(None, max_length=255)
    contact_person: Optional[str] = Field(None, max_length=255)
    designation: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=50)
    email_address: Optional[str] = Field(None, max_length=255)
    status: Optional[bool] = Field(None)


class ContactDiaryPut(BaseModel):
    office_department: str = Field(..., max_length=255)
    contact_person: str = Field(..., max_length=255)
    designation: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=50)
    email_address: Optional[str] = Field(None, max_length=255)
    status: bool
