from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from backend.meta import DownloadStatus


class DownloadResponse(BaseModel):
    id: int
    document_title: str
    document_type: Optional[str]
    department_id: Optional[int]
    description: Optional[str]
    file_path: str = Field(..., description="S3 key or storage path")
    file_url: Optional[str]
    status: DownloadStatus
    uploaded_by: Optional[int]
    uploaded_on: datetime


class DownloadsListResponse(BaseModel):
    downloads: list[DownloadResponse] = []
    total: Optional[int]
