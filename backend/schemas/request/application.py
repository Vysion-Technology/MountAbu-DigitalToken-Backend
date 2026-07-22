from typing import Optional, List

from backend.meta import (
    ApplicationType,
    CommentType,
    PropertyUsageType,
    WorkflowAction,
    ApplicationPhaseStatus,
    StructureType,
    JurisdictionZone,
    UserRole,
)
from pydantic import BaseModel, Field, model_validator


class PhaseStatusUpdateRequest(BaseModel):
    """Request schema for updating a phase's status (Hold/Terminate/Activate)."""

    status: ApplicationPhaseStatus = Field(..., description="Target status for the phase")


class ApplicationMaterialCreate(BaseModel):
    name: str = Field(..., description="Material Name")
    unit: str = Field(..., description="Material Unit")


class ApplicationMaterialRequirements(BaseModel):
    material_id: Optional[int] = Field(None, description="Material ID")
    custom_name: Optional[str] = Field(None, description="Custom Material Name")
    custom_unit: Optional[str] = Field(None, description="Custom Material Unit")
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
    existing_structure: Optional[StructureType] = Field(None, description="Existing Structure Type")
    construction_floor: Optional[StructureType] = Field(None, description="Construction Floor Level")
    jurisdiction_zone: JurisdictionZone = Field(JurisdictionZone.ULB, description="Jurisdiction Zone (ULB / UIT)")
    ward_id: int = Field(..., description="Ward/Zone ID")
    organization_name: Optional[str] = Field(None, description="Organization Name")

    type: ApplicationType = Field(..., description="Application Type")
    description: Optional[str] = Field(None, description="Application Description")
    material_requirements: list[ApplicationMaterialRequirements] = Field(
        ..., description="Application Material Requirements"
    )

    @model_validator(mode="after")
    def validate_structure_and_floor(self) -> "ApplicationCreate":
        # Property usage organization name validation
        if self.property_usage in (PropertyUsageType.COMMERCIAL, PropertyUsageType.GOVERNMENT):
            if not self.organization_name or not self.organization_name.strip():
                raise ValueError(
                    f"Organization name is required when property usage is {self.property_usage.value}"
                )
        else:
            self.organization_name = None

        # If either is None, allow (since by default it can be null)
        if self.existing_structure is None or self.construction_floor is None:
            return self

        # Application type NEW
        if self.type == ApplicationType.NEW:
            expected_floors = []
            if self.existing_structure == StructureType.NONE:
                expected_floors = [StructureType.FENCING, StructureType.G]
            elif self.existing_structure == StructureType.FENCING:
                expected_floors = [StructureType.G]
            elif self.existing_structure == StructureType.G:
                expected_floors = [StructureType.G_1]
            elif self.existing_structure == StructureType.G_1:
                expected_floors = [StructureType.G_2]
            elif self.existing_structure == StructureType.G_2:
                expected_floors = [StructureType.G_3]
            elif self.existing_structure == StructureType.G_3:
                raise ValueError("Cannot request new construction above G+3 structure")

            if self.construction_floor not in expected_floors:
                raise ValueError(
                    f"For new construction with existing structure '{self.existing_structure.value}', "
                    f"the construction floor must be one of: {[f.value for f in expected_floors]}"
                )

        # Application type RENOVATION
        elif self.type == ApplicationType.RENOVATION:
            structure_order = [
                StructureType.NONE,
                StructureType.FENCING,
                StructureType.G,
                StructureType.G_1,
                StructureType.G_2,
                StructureType.G_3,
            ]
            existing_idx = structure_order.index(self.existing_structure)
            construction_idx = structure_order.index(self.construction_floor)
            if construction_idx > existing_idx:
                raise ValueError(
                    f"For renovation/repair, the construction floor cannot exceed the existing structure. "
                    f"Max permitted is '{self.existing_structure.value}', got '{self.construction_floor.value}'"
                )

        return self


class CommentRequest(BaseModel):
    comment: str = Field(..., description="Comment")
    comment_type: CommentType = Field(
        CommentType.GENERAL, description="Type of comment"
    )
    media_paths: Optional[List[str]] = Field(
        None, description="Optional media/file paths attached to the comment"
    )


class MaterialRequest(BaseModel):
    material_id: Optional[int] = Field(None, description="Material ID")
    custom_name: Optional[str] = Field(None, description="Custom Material Name")
    custom_unit: Optional[str] = Field(None, description="Custom Material Unit")
    material_qty: int = Field(..., description="Material Quantity")


class PhaseMaterialEntry(BaseModel):
    """Material allocation for a specific phase during token generation."""

    phase: int = Field(..., ge=1, description="Phase number")
    material_id: Optional[int] = Field(None, description="Material ID")
    custom_name: Optional[str] = Field(None, description="Custom Material Name")
    custom_unit: Optional[str] = Field(None, description="Custom Material Unit")
    quantity: int = Field(..., ge=1, description="Permitted quantity for this phase")


class WorkflowActionRequest(BaseModel):
    """Request body for workflow actions (approve/reject/object/forward)."""

    action: WorkflowAction = Field(..., description="Workflow action to perform")
    remarks: Optional[str] = Field(None, description="Remarks for the action")
    phase: Optional[int] = Field(
        None,
        description="Specific phase number to generate (for GENERATE_TOKENS)",
        ge=1,
        le=10,
    )
    phase_materials: Optional[List[PhaseMaterialEntry]] = Field(
        None,
        description="Materials per phase (required for GENERATE_TOKENS)",
    )
    objection_to_role: Optional[UserRole] = Field(
        None,
        description="Specific role to redirect the objection to",
    )
    objection_to_roles: Optional[List[UserRole]] = Field(
        None,
        description="List of roles to direct objections to",
    )
    role_remarks: Optional[dict] = Field(
        None,
        description="Per-role objection remarks mapping (role -> remark string)",
    )
    reverted_document_url: Optional[str] = Field(
        None,
        description="URL of uploaded Objection Reverted Data PDF",
    )
    clear_objection_role: Optional[UserRole] = Field(
        None,
        description="Specific objection role being cleared by Nodal/Commissioner/Superadmin",
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


class InspectionReportUpdate(BaseModel):
    """JEN updates an inspection report."""

    latitude: Optional[float] = Field(None, description="GPS Latitude")
    longitude: Optional[float] = Field(None, description="GPS Longitude")
    remarks: Optional[str] = Field(None, min_length=5, description="Inspection remarks")
    media_paths: Optional[List[str]] = Field(
        None, description="Media/photo paths from inspection"
    )
    recommended_phases: Optional[int] = Field(
        None, ge=1, le=10, description="JEN's recommended number of phases"
    )



class NakaMaterialItem(BaseModel):
    """Single material + quantity in a naka entry."""

    material_id: Optional[int] = Field(None, description="Material ID")
    custom_name: Optional[str] = Field(None, description="Custom Material Name")
    custom_unit: Optional[str] = Field(None, description="Custom Material Unit")
    quantity_brought: float = Field(..., ge=0.01, description="Quantity brought")


class NakaEntryCreate(BaseModel):
    """Naka incharge logs materials brought at checkpoint."""

    materials: List[NakaMaterialItem] = Field(
        ..., min_length=1, description="Materials brought"
    )
    vehicle_number: Optional[str] = Field(None, description="Vehicle number")
    vehicle_type: Optional[str] = Field(None, description="Vehicle type")
    latitude: Optional[float] = Field(None, description="GPS Latitude")
    longitude: Optional[float] = Field(None, description="GPS Longitude")
    remarks: Optional[str] = Field(None, description="Remarks")
    vehicle_plate_image: Optional[str] = Field(None, description="Vehicle number plate image path")
    entry_proof_images: List[str] = Field(default_factory=list, description="Entry proof image paths")


# Resolve forward reference
WorkflowActionRequest.model_rebuild()
