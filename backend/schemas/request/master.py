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


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    type: Optional[str] = None
    status: Optional[bool] = None


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


class ComplaintCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[bool] = None
