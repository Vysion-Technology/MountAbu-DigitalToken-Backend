from typing import Optional, List

from backend.meta import ApplicationType, CommentType, PropertyUsageType, WorkflowAction
from pydantic import BaseModel, Field


class ApplicationMaterialCreate(BaseModel):
    name: str = Field(..., description="Material Name")
    unit: str = Field(..., description="Material Unit")


class ApplicationMaterialRequirements(BaseModel):
    material_id: int = Field(..., description="Material ID")
    material_qty: int = Field(..., description="Material Quantity")


class ApplicationCreate(BaseModel):
    # Applicant Details
    applicant_name: str = Field(..., description="Applicant Name (As per Aadhar)")
    father_name: str = Field(..., description="Father's Name (As per Aadhar)")
    # Mobile is now fetched from User
    email: Optional[str] = Field(None, description="Email Address")
    current_address: str = Field(..., description="Current Address")

    # Property & Work Details
    property_address: str = Field(..., description="Property Address")
    title: str = Field(..., description="Application Title")
    work_description: str = Field(..., description="Work Description")
    contractor_name: Optional[str] = Field(None, description="Contractor Name")

    # Classification
    is_agriculture_land: bool = Field(
        ..., description="Is property on agriculture land?"
    )
    property_usage: PropertyUsageType = Field(..., description="Property Usage Type")
    ward_id: int = Field(..., description="Ward/Zone ID")

    type: ApplicationType = Field(..., description="Application Type")
    description: Optional[str] = Field(None, description="Application Description")
    material_requirements: list[ApplicationMaterialRequirements] = Field(
        ..., description="Application Material Requirements"
    )


class CommentRequest(BaseModel):
    comment: str = Field(..., description="Comment")
    comment_type: CommentType = Field(
        CommentType.GENERAL, description="Type of comment"
    )
    media_paths: Optional[List[str]] = Field(
        None, description="Optional media/file paths attached to the comment"
    )


class MaterialRequest(BaseModel):
    material_id: int = Field(..., description="Material ID")
    material_qty: int = Field(..., description="Material Quantity")


class PhaseMaterialEntry(BaseModel):
    """Material allocation for a specific phase during token generation."""

    phase: int = Field(..., ge=1, description="Phase number")
    material_id: int = Field(..., description="Material ID")
    quantity: int = Field(..., ge=1, description="Permitted quantity for this phase")


class WorkflowActionRequest(BaseModel):
    """Request body for workflow actions (approve/reject/object/forward)."""

    action: WorkflowAction = Field(..., description="Workflow action to perform")
    remarks: Optional[str] = Field(None, description="Remarks for the action")
    num_stages: Optional[int] = Field(
        None,
        description="Number of phases/stages for token generation (required for GENERATE_TOKENS)",
        ge=1,
        le=10,
    )
    phase_materials: Optional[List[PhaseMaterialEntry]] = Field(
        None,
        description="Materials per phase (required for GENERATE_TOKENS)",
    )


class InspectionReportCreate(BaseModel):
    """JEN creates an inspection report."""

    latitude: Optional[float] = Field(None, description="GPS Latitude")
    longitude: Optional[float] = Field(None, description="GPS Longitude")
    remarks: str = Field(..., min_length=5, description="Inspection remarks")
    media_paths: Optional[List[str]] = Field(
        None, description="Media/photo paths from inspection"
    )
    recommended_phases: Optional[int] = Field(
        None, ge=1, le=10, description="JEN's recommended number of phases"
    )
    # JEN also submits materials per phase
    phase_materials: Optional[List[PhaseMaterialEntry]] = Field(
        None, description="Recommended materials per phase"
    )


class NakaEntryCreate(BaseModel):
    """Naka incharge logs materials brought at checkpoint."""

    material_id: int = Field(..., description="Material ID")
    quantity_brought: int = Field(..., ge=1, description="Quantity brought")
    vehicle_number: Optional[str] = Field(None, description="Vehicle number")
    remarks: Optional[str] = Field(None, description="Remarks")
    media_path: Optional[str] = Field(None, description="Photo/media path")


# Resolve forward reference
WorkflowActionRequest.model_rebuild()
