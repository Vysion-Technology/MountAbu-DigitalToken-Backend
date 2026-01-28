from backend.meta import ApplicationStatus, ApplicationType, ApplicationDocumentType
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class ApplicationDocumentResponse(BaseModel):
    id: int
    document_path: str
    document_type: ApplicationDocumentType
    document_name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ApplicationResponse(BaseModel):
    """..."""

    id: int
    user_id: int
    status: ApplicationStatus
    type: ApplicationType
    num_stages: Optional[int]
    documents: List[ApplicationDocumentResponse] = []

    model_config = ConfigDict(extra="ignore", from_attributes=True)
