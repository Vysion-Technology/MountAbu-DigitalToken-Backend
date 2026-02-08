from backend.meta import (
    ApplicationStatus,
    ApplicationType,
    ApplicationDocumentType,
    PropertyUsageType,
)
from pydantic import BaseModel, ConfigDict, model_validator

from typing import Optional, List


class ApplicationDocumentResponse(BaseModel):
    id: int
    document_path: str
    document_type: ApplicationDocumentType
    document_name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ApplicationMaterialResponse(BaseModel):
    """Response schema for application materials."""

    id: int
    material_id: int
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class CommentResponse(BaseModel):
    """Response schema for application comments."""

    id: int
    application_id: int
    comment: str
    comment_by: int
    commenter_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_commenter_name(cls, data):
        """Extract commenter name from the relationship."""
        if hasattr(data, "commenter") and data.commenter:
            data = dict(
                id=data.id,
                application_id=data.application_id,
                comment=data.comment,
                comment_by=data.comment_by,
                commenter_name=data.commenter.name,
            )
        return data


class ApplicationResponse(BaseModel):
    """Application Response Schema."""

    id: int
    user_id: int

    # Applicant Details
    applicant_name: str
    father_name: str
    mobile: str
    email: Optional[str]
    current_address: str

    # Property & Work Details
    property_address: str
    title: str
    work_description: str
    contractor_name: Optional[str]

    # Classification
    is_agriculture_land: bool
    property_usage: PropertyUsageType
    department_id: Optional[int]
    ward_id: Optional[int]
    # In future we can include nested objects:
    # department: Optional[DepartmentResponse]
    # ward: Optional[WardResponse]

    ward_zone: Optional[str] = (
        None  # Deprecated, keeping for backward compatibility if needed, or remove.
    )
    # Removing ward_zone as it is replaced by ward_id

    description: Optional[str] = None
    status: ApplicationStatus
    type: ApplicationType
    num_stages: Optional[int]
    documents: List[ApplicationDocumentResponse] = []
    materials: List[ApplicationMaterialResponse] = []
    comments: List[CommentResponse] = []

    model_config = ConfigDict(extra="ignore", from_attributes=True)

