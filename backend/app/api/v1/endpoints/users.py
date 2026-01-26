"""User management endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_authority
from app.models import User, Application, ApplicationStatus, UserBlacklistStatus
from app.schemas import (
    ProfileUpdate,
    SuccessResponse,
    UserProfileWithStats,
)

router = APIRouter()


@router.get("/profile", response_model=SuccessResponse)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get current user's profile with statistics."""
    # Get application stats
    stats_result = await db.execute(
        select(
            func.count(Application.id).label("total"),
            func.count(Application.id)
            .filter(Application.status == ApplicationStatus.APPROVED)
            .label("approved"),
            func.count(Application.id)
            .filter(Application.status == ApplicationStatus.REJECTED)
            .label("rejected"),
            func.count(Application.id)
            .filter(
                Application.status.in_(
                    [
                        ApplicationStatus.SUBMITTED,
                        ApplicationStatus.SDM_REVIEW,
                        ApplicationStatus.CMS_REVIEW,
                        ApplicationStatus.JEN_INSPECTION,
                    ]
                )
            )
            .label("pending"),
        ).where(Application.applicant_id == current_user.id)
    )
    stats = stats_result.one()

    # Get blacklist status
    blacklist_data = None
    if current_user.blacklist_status:
        bs = current_user.blacklist_status
        blacklist_data = {
            "is_blacklisted": bs.is_blacklisted,
            "consecutive_rejections": bs.consecutive_rejections,
            "warning_issued": bs.warning_issued,
        }

    return SuccessResponse(
        data={
            "id": str(current_user.id),
            "user_type": current_user.user_type.value,
            "name": current_user.name,
            "mobile": current_user.mobile,
            "email": current_user.email,
            "aadhaar_verified": current_user.aadhaar_verified,
            "preferred_language": current_user.preferred_language,
            "address": {
                "line1": current_user.address_line1,
                "line2": current_user.address_line2,
                "city": current_user.city,
                "state": current_user.state,
                "pincode": current_user.pincode,
            },
            "stats": {
                "total_applications": stats.total,
                "approved_applications": stats.approved,
                "rejected_applications": stats.rejected,
                "pending_applications": stats.pending,
            },
            "blacklist_status": blacklist_data,
            "created_at": current_user.created_at.isoformat(),
        }
    )


@router.put("/profile", response_model=SuccessResponse)
async def update_profile(
    updates: ProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update user profile."""
    if updates.name:
        current_user.name = updates.name
    if updates.email:
        current_user.email = updates.email
    if updates.preferred_language:
        current_user.preferred_language = updates.preferred_language

    if updates.address:
        addr = updates.address
        if addr.line1:
            current_user.address_line1 = addr.line1
        if addr.line2:
            current_user.address_line2 = addr.line2
        if addr.city:
            current_user.city = addr.city
        if addr.state:
            current_user.state = addr.state
        if addr.pincode:
            current_user.pincode = addr.pincode

    return SuccessResponse(
        message="Profile updated successfully",
        data={"id": str(current_user.id), "name": current_user.name},
    )


@router.get("/authorities", response_model=SuccessResponse)
async def list_authorities(
    current_user: Annotated[User, Depends(get_current_authority)],
    db: Annotated[AsyncSession, Depends(get_db)],
    role: str = None,
    status: str = "active",
    page: int = 1,
    limit: int = 20,
):
    """List all authorities (admin only)."""
    from app.models import UserType, UserStatus, Role

    # Build query
    query = select(User).where(
        User.user_type == UserType.AUTHORITY,
        User.is_deleted == False,
    )

    if status:
        query = query.where(User.status == UserStatus(status.upper()))

    if role:
        query = query.join(Role).where(Role.name == role.upper())

    # Get total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    # Paginate
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    authorities = result.scalars().all()

    return SuccessResponse(
        data={
            "authorities": [
                {
                    "id": str(auth.id),
                    "name": auth.name,
                    "email": auth.email,
                    "mobile": auth.mobile,
                    "role": auth.role.name.value if auth.role else None,
                    "department": auth.department,
                    "designation": auth.designation,
                    "status": auth.status.value,
                    "last_login": auth.last_login_at.isoformat()
                    if auth.last_login_at
                    else None,
                }
                for auth in authorities
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
            },
        }
    )
