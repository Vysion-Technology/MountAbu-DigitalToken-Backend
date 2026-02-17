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
    access_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def compute_access_url(cls, data):
        """Generate a signed download URL from *document_path*."""
        from backend.services.storage import generate_signed_file_url

        path = None
        if hasattr(data, "document_path"):
            path = data.document_path
        elif isinstance(data, dict):
            path = data.get("document_path")

        if path:
            url = generate_signed_file_url(path)
            if hasattr(data, "__dict__"):
                return {
                    "id": data.id,
                    "document_path": path,
                    "document_type": data.document_type,
                    "document_name": getattr(data, "document_name", None),
                    "access_url": url,
                }
            else:
                data["access_url"] = url
        return data


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
    transport_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def compute_transport_code(cls, data):
        """Generate the HMAC transport code from application_id + phase."""
        from backend.core.transport_code import encode_transport_code
        if hasattr(data, "application_id") and hasattr(data, "phase"):
            app_id = data.application_id
            phase = data.phase
        elif isinstance(data, dict):
            app_id = data.get("application_id")
            phase = data.get("phase")
        else:
            return data
        if app_id is not None and phase is not None:
            if hasattr(data, "__dict__"):
                # ORM model — convert to dict for mutation
                d = {
                    "id": data.id,
                    "application_id": app_id,
                    "phase": phase,
                    "name": getattr(data, "name", None),
                    "status": data.status,
                    "activated_at": getattr(data, "activated_at", None),
                    "completed_at": getattr(data, "completed_at", None),
                    "transport_code": encode_transport_code(app_id, phase),
                }
                return d
            else:
                data["transport_code"] = encode_transport_code(app_id, phase)
        return data


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
    access_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def compute_access_url(cls, data):
        from backend.services.storage import generate_signed_file_url
        path = getattr(data, "media_path", None) if hasattr(data, "media_path") else (data.get("media_path") if isinstance(data, dict) else None)
        if path:
            url = generate_signed_file_url(path)
            if hasattr(data, "__dict__") and not isinstance(data, dict):
                d = {k: getattr(data, k) for k in ["id", "application_id", "phase", "material_id", "quantity_brought", "entry_by", "entry_at", "vehicle_number", "remarks", "media_path"]}
                d["access_url"] = url
                return d
            elif isinstance(data, dict):
                data["access_url"] = url
        return data


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

