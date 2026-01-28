from backend.meta import UserRole
from backend.schemas.base.auth import UserDetails


async def get_current_user(token: str) -> UserDetails:
    """Get user details from the token"""
    return UserDetails(role=UserRole.CITIZEN, user_id=-1)


async def get_current_user_id(token: str) -> int:
    """Get user id from the token"""
    return -1
