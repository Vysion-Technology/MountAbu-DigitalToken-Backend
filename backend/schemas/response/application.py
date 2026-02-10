from datetime import datetime

from backend.meta import (
    ApplicationStatus,
    ApplicationType,
    ApplicationDocumentType,
    ApplicationPhaseStatus,
    CommentType,
    PropertyUsageType,
    WorkflowAction,
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
    comment_type: Optional[CommentType] = CommentType.GENERAL
    media_paths: Optional[list] = None
    created_at: Optional[datetime] = None

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
                comment_type=getattr(data, "comment_type", CommentType.GENERAL),
                media_paths=getattr(data, "media_paths", None),
                created_at=getattr(data, "created_at", None),
            )
        return data


class PhaseMaterialResponse(BaseModel):
    """Response schema for phase-level materials."""
    id: int
    application_id: int
    phase: int
    material_id: int
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class PhaseResponse(BaseModel):
    """Response schema for application phases."""
    id: int
    application_id: int
    phase: int
    name: Optional[str] = None
    status: ApplicationPhaseStatus
    activated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NakaEntryResponse(BaseModel):
    """Response for a Naka checkpoint entry."""
    id: int
    application_id: int
    phase: int
    material_id: int
    quantity_brought: int
    entry_by: int
    entry_at: datetime
    vehicle_number: Optional[str] = None
    remarks: Optional[str] = None
    media_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InspectionReportResponse(BaseModel):
    """Response for an inspection report."""
    id: int
    application_id: int
    inspected_by: int
    inspected_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    remarks: str
    media_paths: Optional[list] = None
    recommended_phases: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ActionLogResponse(BaseModel):
    """Response for an action log entry."""
    id: int
    application_id: int
    action: WorkflowAction
    from_status: ApplicationStatus
    to_status: ApplicationStatus
    performed_by: int
    performed_at: datetime
    remarks: Optional[str] = None
    phase: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


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

    ward_zone: Optional[str] = None

    description: Optional[str] = None
    status: ApplicationStatus
    type: ApplicationType
    num_stages: Optional[int]
    documents: List[ApplicationDocumentResponse] = []
    materials: List[ApplicationMaterialResponse] = []
    comments: List[CommentResponse] = []

    model_config = ConfigDict(extra="ignore", from_attributes=True)

