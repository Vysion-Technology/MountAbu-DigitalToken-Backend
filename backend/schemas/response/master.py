from datetime import datetime
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
    created_at: Optional[datetime] = None
    created_by: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)
