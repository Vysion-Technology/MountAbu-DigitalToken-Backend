from typing import Optional

from backend.meta import ApplicationType, PropertyUsageType, DepartmentType
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
    mobile: str = Field(..., description="Mobile Number")
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
    department: DepartmentType = Field(..., description="Selected Department")
    ward_zone: str = Field(..., description="Ward/Zone")

    type: ApplicationType = Field(..., description="Application Type")
    description: Optional[str] = Field(None, description="Application Description")
    material_requirements: list[ApplicationMaterialRequirements] = Field(
        ..., description="Application Material Requirements"
    )


class CommentRequest(BaseModel):
    comment: str = Field(..., description="Comment")


class MaterialRequest(BaseModel):
    material_id: int = Field(..., description="Material ID")
    material_qty: int = Field(..., description="Material Quantity")
