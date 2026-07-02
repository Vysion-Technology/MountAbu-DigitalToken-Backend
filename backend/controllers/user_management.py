from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dao.user import UserDAO
from backend.database import get_db
from backend.meta import UserRole, JurisdictionZone
from backend.middlewares.auth import get_current_user
from backend.schemas.base.auth import UserDetails

from backend.services.audit import AuditService
from backend.meta.audit import AuditAction

router = APIRouter()
user_dao = UserDAO()
audit_service = AuditService()


class UserFilter(str, Enum):
    CITIZEN = "CITIZEN"
    OFFICIAL = "OFFICIAL"


class UserResponse(BaseModel):
    id: int
    name: str
    mobile: str
    role: UserRole
    username: Optional[str] = None
    is_active: bool
    jurisdiction_zone: Optional[JurisdictionZone] = None

    class Config:
        from_attributes = True


async def get_current_official(
    current_user: UserDetails = Depends(get_current_user),
) -> UserDetails:
    allowed_roles = [
        UserRole.SUPERADMIN,
        UserRole.NODAL_OFFICER,
        UserRole.COMMISSIONER,
    ]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )
    return current_user


@router.get(
    "/users",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
)
async def list_users(
    filter: UserFilter = Query(
        ..., description="Filter users by type (CITIZEN or OFFICIAL)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_current_official),
):
    """
    List users based on the filter.
    Only SUPERADMIN, NODAL_OFFICER, and COMMISSIONER can access this.
    """
    is_citizen = filter == UserFilter.CITIZEN
    users = await user_dao.get_users_filtered(db, is_citizen=is_citizen)
    await audit_service.log(
        db,
        "USER",
        AuditAction.VIEWED,
        current_user.user_id,
        new_state={"filter": filter.value},
    )
    await db.commit()
    return users
