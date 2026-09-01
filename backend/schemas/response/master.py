from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict



class UserSummary(BaseModel):
    id: int
    name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class WardResponse(BaseModel):
    id: int
    name: str
    code: str
    type: str
    description: Optional[str]
    status: bool
    created_at: Optional[datetime] = None
    created_by: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentResponse(BaseModel):
    id: int
    name: str
    code: str
    type: str
    status: bool
    jen_id: Optional[int] = None
    jen: Optional[UserSummary] = None
    created_at: Optional[datetime] = None
    created_by: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    id: int
    name: str
    code: str
    permissions: Optional[str]
    status: bool
    created_at: Optional[datetime] = None
    created_by: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)


class ComplaintCategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: bool
    department_id: Optional[int] = None
    created_at: Optional[datetime] = None
    created_by: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)


class MaterialResponse(BaseModel):
    id: int
    name: str
    unit: str
    status: bool = True
    created_at: Optional[datetime] = None
    created_by: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)


class SlotDefinitionResponse(BaseModel):
    id: int
    name: str
    start_time: str
    end_time: str
    max_capacity: int
    applicable_days: str = "MON,TUE,WED,THU,FRI,SAT,SUN"
    grace_period_minutes: int = 30
    is_active: bool
    created_at: Optional[datetime] = None
    created_by: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)


class VehicleTypeResponse(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool
    created_at: Optional[datetime] = None
    created_by: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduleBlackoutResponse(BaseModel):
    id: int
    blackout_date: date
    reason: str
    is_full_day: bool
    slot_id: Optional[int] = None
    slot_name: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    created_by: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)


