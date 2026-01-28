from backend.meta import ApplicationType
from pydantic import BaseModel, Field


class ApplicationMaterialCreate(BaseModel):
    name: str = Field(..., description="Material Name")
    unit: str = Field(..., description="Material Unit")


class ApplicationMaterialRequirements(BaseModel):
    material_id: int = Field(..., description="Material ID")
    material_qty: int = Field(..., description="Material Quantity")


class ApplicationCreate(BaseModel):
    title: str = Field(..., description="Application Title")
    type: ApplicationType = Field(..., description="Application Type")
    description: str = Field(..., description="Application Description")
    material_requirements: list[ApplicationMaterialRequirements] = Field(
        ..., description="Application Material Requirements"
    )


class CommentRequest(BaseModel):
    comment: str = Field(..., description="Comment")


class MaterialRequest(BaseModel):
    material_id: int = Field(..., description="Material ID")
    material_qty: int = Field(..., description="Material Quantity")
