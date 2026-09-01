from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class TollPlazaMaterialItem(BaseModel):
    material_id: Optional[int] = Field(None, description="Material ID")
    material_name: str = Field(..., description="Material Name")
    unit: str = Field(..., description="Material Unit")
    quantity: float = Field(..., description="Quantity brought in this entry")

class TollPlazaVerifyResponse(BaseModel):
    verified: bool = Field(..., description="Whether verification was successful")
    naka_entry_id: int = Field(..., description="The ID of the Naka vehicle entry")
    vehicle_number: str = Field(..., description="The vehicle plate number")
    entry_at: datetime = Field(..., description="Timestamp when the Naka incharge logged the entry")
    verified_at: datetime = Field(..., description="Timestamp when verified at Toll Plaza")
    materials: List[TollPlazaMaterialItem] = Field(default_factory=list, description="Materials carried in this vehicle entry")
