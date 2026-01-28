from pydantic import BaseModel, Field


class UpdateUserRolesRequest(BaseModel):
    """Request schema for updating user roles."""

    user_id: str = Field(..., description="User ID")
    roles: str = Field(..., description="Roles")
