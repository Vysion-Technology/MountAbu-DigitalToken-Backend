from typing import Optional
from pydantic import BaseModel, ConfigDict


class WardResponse(BaseModel):
    id: int
    name: str
    code: str
    type: str
    description: Optional[str]
    status: bool

    model_config = ConfigDict(from_attributes=True)


class DepartmentResponse(BaseModel):
    id: int
    name: str
    code: str
    type: str
    status: bool

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    id: int
    name: str
    code: str
    permissions: Optional[str]
    status: bool

    model_config = ConfigDict(from_attributes=True)


class ComplaintCategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: bool

    model_config = ConfigDict(from_attributes=True)
