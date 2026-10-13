from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class VehicleScheduleCreate(BaseModel):
    token_id: int = Field(..., description="Active Token ID to schedule vehicle for")
    slot_id: int = Field(..., description="Slot definition ID")
    schedule_date: date = Field(..., description="Date of transit (YYYY-MM-DD)")
    vehicle_number: str = Field(..., min_length=4, max_length=20, description="Vehicle Registration Number (e.g. RJ 27 GA 1234)")
    vehicle_type_id: Optional[int] = Field(None, description="Vehicle Type Master ID")
    driver_name: Optional[str] = Field(None, description="Driver's Name")
    driver_mobile: Optional[str] = Field(None, description="Driver's Mobile")
