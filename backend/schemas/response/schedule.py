from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.meta import VehicleScheduleStatus, ScheduleComplianceStatus


class AvailableSlotItemResponse(BaseModel):
    slot_id: int
    name: str
    start_time: str
    end_time: str
    max_capacity: int
    booked_count: int
    available_capacity: int
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


class AvailableSlotsResponse(BaseModel):
    date: date
    slots: List[AvailableSlotItemResponse]


class VehicleScheduleResponse(BaseModel):
    id: int
    schedule_code: str
    application_id: int
    token_id: int
    phase: int
    user_id: int
    slot_id: int
    slot_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    schedule_date: datetime
    vehicle_number: str
    vehicle_type_id: Optional[int] = None
    vehicle_type_name: Optional[str] = None
    status: VehicleScheduleStatus
    created_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    transport_code: Optional[str] = None
    property_address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TokenScheduleStatusResponse(BaseModel):
    has_active_schedule: bool
    active_schedule: Optional[VehicleScheduleResponse] = None
