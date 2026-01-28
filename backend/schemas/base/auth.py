from pydantic import BaseModel, Field
from backend.meta import UserRole


class UserDetails(BaseModel):
    role: UserRole
    user_id: int = Field(..., description="User ID", default=-1)
