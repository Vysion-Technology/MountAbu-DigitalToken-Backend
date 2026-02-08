from typing import Optional
from pydantic import BaseModel, Field


class DownloadCreate(BaseModel):
    document_title: str = Field(..., description="Title of the document")
    document_type: Optional[str] = Field(None, description="Type of the document, e.g., Guidelines, Form")
    department_id: Optional[int] = Field(None, description="Department id that owns the document")
    description: Optional[str] = Field(None, description="Short description of the document")
    status: Optional[str] = Field("ACTIVE", description="Status - ACTIVE or INACTIVE")


class DownloadUpdate(BaseModel):
    document_title: Optional[str] = Field(None)
    document_type: Optional[str] = Field(None)
    department_id: Optional[int] = Field(None)
    description: Optional[str] = Field(None)
    status: Optional[str] = Field(None)
