from pydantic import BaseModel, Field
from backend.meta import UserRole


class UserDetails(BaseModel):
    role: UserRole
    user_id: int = Field(default=-1, description="User ID")
