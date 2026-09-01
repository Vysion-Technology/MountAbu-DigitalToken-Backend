from typing import Optional
from pydantic import BaseModel, Field


class WardCreate(BaseModel):
    name: str = Field(..., description="Name of the Ward/Zone")
    code: str = Field(..., description="Unique Code")
    type: str = Field(..., description="Type: Ward or Zone")
    description: Optional[str] = Field(None, description="Description")
    status: bool = Field(True, description="Active Status")


class WardUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[bool] = None


class DepartmentCreate(BaseModel):
    name: str = Field(..., description="Name of the Department")
    code: str = Field(..., description="Unique Code")
    type: str = Field(..., description="Type of Department")
    status: bool = Field(True, description="Active Status")
    jen_id: Optional[int] = Field(None, description="Primary JEN User ID")


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    type: Optional[str] = None
    status: Optional[bool] = None
    jen_id: Optional[int] = None


class RoleCreate(BaseModel):
    name: str = Field(..., description="Name of the Role")
    code: str = Field(..., description="Unique Code")
    permissions: Optional[str] = Field(None, description="Permissions (JSON/CSV)")
    status: bool = Field(True, description="Active Status")


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    permissions: Optional[str] = None
    status: Optional[bool] = None


class ComplaintCategoryCreate(BaseModel):
    name: str = Field(..., description="Name of the Category")
    description: Optional[str] = Field(None, description="Description")
    status: bool = Field(True, description="Active Status")
    department_id: Optional[int] = Field(None, description="Mapped Department ID")


class ComplaintCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[bool] = None
    department_id: Optional[int] = None


class MaterialCreate(BaseModel):
    name: str = Field(..., description="Material Name")
    unit: str = Field(..., description="Unit (e.g., kg, bags)")
    status: bool = Field(True, description="Active status")


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    status: Optional[bool] = None


class SlotDefinitionCreate(BaseModel):
    name: str = Field(..., description="Name of the slot (e.g., Slot 1: 08:00 AM - 10:00 AM)")
    start_time: str = Field(..., description="Start time (e.g., 08:00)")
    end_time: str = Field(..., description="End time (e.g., 10:00)")
    max_capacity: int = Field(20, description="Maximum vehicle capacity for this slot")
    is_active: bool = Field(True, description="Is slot active")


class SlotDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    max_capacity: Optional[int] = None
    is_active: Optional[bool] = None


class VehicleTypeCreate(BaseModel):
    name: str = Field(..., description="Vehicle type name (e.g., Pickup (4 Wheeler))")
    code: str = Field(..., description="Unique vehicle type code (e.g., PICKUP_4W)")
    is_active: bool = Field(True, description="Is vehicle type active")


class VehicleTypeUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None

