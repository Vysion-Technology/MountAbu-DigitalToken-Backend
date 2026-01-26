"""Blacklist management endpoints."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.v1.deps import get_current_authority
from app.models import User, UserBlacklistStatus, ApplicationRejection
from app.schemas import WhitelistRequest, SuccessResponse
from app.services.blacklist_service import BlacklistService

router = APIRouter()


@router.get("", response_model=SuccessResponse)
async def list_blacklisted_users(
    current_user: Annotated[User, Depends(get_current_authority)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Optional[str] = Query("blacklisted", alias="status"),
    page: int = 1,
    limit: int = 20,
):
    """List blacklisted users (SDM/CMS only)."""
    # Check if user has permission
    if current_user.role and current_user.role.name.value not in [
        "SDM",
        "CMS_UIT",
        "CMS_ULB",
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SDM/CMS can view blacklist",
        )

    # Build query
    query = select(UserBlacklistStatus).options(selectinload(UserBlacklistStatus.user))

    if status_filter == "blacklisted":
        query = query.where(UserBlacklistStatus.is_blacklisted == True)
    elif status_filter == "all":
        pass  # No filter

    # Count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    # Paginate
    query = (
        query.order_by(UserBlacklistStatus.blacklisted_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(query)
    blacklist_records = result.scalars().all()

    return SuccessResponse(
        data={
            "users": [
                {
                    "user_id": str(record.user_id),
                    "name": record.user.name,
                    "mobile": record.user.mobile,
                    "is_blacklisted": record.is_blacklisted,
                    "consecutive_rejections": record.consecutive_rejections,
                    "total_rejections": record.total_rejections,
                    "blacklisted_at": record.blacklisted_at.isoformat()
                    if record.blacklisted_at
                    else None,
                    "blacklist_reason": record.blacklist_reason,
                    "whitelisted_at": record.whitelisted_at.isoformat()
                    if record.whitelisted_at
                    else None,
                }
                for record in blacklist_records
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
            },
            "summary": {
                "total_blacklisted": total if status_filter == "blacklisted" else None,
            },
        }
    )


@router.get("/{user_id}/history", response_model=SuccessResponse)
async def get_rejection_history(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_authority)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get user's rejection history."""
    # Get user
    user_result = await db.execute(
        select(User)
        .options(selectinload(User.blacklist_status))
        .where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get rejection history
    rejection_result = await db.execute(
        select(ApplicationRejection)
        .where(ApplicationRejection.user_id == user_id)
        .order_by(ApplicationRejection.rejected_at.desc())
    )
    rejections = rejection_result.scalars().all()

    # Current status
    bs = user.blacklist_status
    current_status = {
        "is_blacklisted": bs.is_blacklisted if bs else False,
        "consecutive_rejections": bs.consecutive_rejections if bs else 0,
        "total_rejections": bs.total_rejections if bs else 0,
        "total_approvals": bs.total_approvals if bs else 0,
        "warning_issued": bs.warning_issued if bs else False,
    }

    # Determine warning level
    if current_status["is_blacklisted"]:
        warning_level = "BLACKLISTED"
    elif current_status["consecutive_rejections"] >= 2:
        warning_level = "HIGH"
    elif current_status["consecutive_rejections"] >= 1:
        warning_level = "MEDIUM"
    else:
        warning_level = "LOW"

    return SuccessResponse(
        data={
            "user_id": str(user_id),
            "name": user.name,
            "mobile": user.mobile,
            "current_status": current_status,
            "warning_level": warning_level,
            "rejection_history": [
                {
                    "application_id": str(rej.application_id),
                    "rejected_at": rej.rejected_at.isoformat(),
                    "rejected_by_role": rej.rejected_by_role,
                    "reason": rej.rejection_reason,
                    "category": rej.rejection_category,
                    "comments": rej.authority_comments,
                    "was_consecutive": rej.was_consecutive,
                    "triggered_blacklist": rej.triggered_blacklist,
                }
                for rej in rejections
            ],
        }
    )


@router.post("/{user_id}/whitelist", response_model=SuccessResponse)
async def whitelist_user(
    user_id: UUID,
    request: WhitelistRequest,
    current_user: Annotated[User, Depends(get_current_authority)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Whitelist a blacklisted user (SDM/CMS only)."""
    # Check permission
    if current_user.role and current_user.role.name.value not in [
        "SDM",
        "CMS_UIT",
        "CMS_ULB",
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SDM/CMS can whitelist users",
        )

    blacklist_service = BlacklistService(db)
    result = await blacklist_service.whitelist_user(
        user_id=user_id,
        whitelisted_by=current_user.id,
        reason=request.reason,
        conditions=request.conditions,
    )

    return SuccessResponse(
        message="User whitelisted successfully",
        data=result,
    )


@router.post("/{user_id}", response_model=SuccessResponse)
async def manually_blacklist_user(
    user_id: UUID,
    reason: str,
    category: str = "MANUAL",
    current_user: Annotated[User, Depends(get_current_authority)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """Manually blacklist a user (SDM only)."""
    # Check permission
    if current_user.role and current_user.role.name.value != "SDM":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SDM can manually blacklist users",
        )

    blacklist_service = BlacklistService(db)
    result = await blacklist_service.manual_blacklist(
        user_id=user_id,
        blacklisted_by=current_user.id,
        reason=reason,
        category=category,
    )

    return SuccessResponse(
        message="User blacklisted",
        data=result,
    )
