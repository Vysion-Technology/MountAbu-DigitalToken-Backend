from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.middlewares.auth import get_current_user
from backend.schemas.response.auth import UserDetails
from backend.schemas.response.common import SuccessResponse
from backend.schemas.response.notification import NotificationListResponse, NotificationItem
from backend.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(db)


@router.get("", response_model=NotificationListResponse)
async def get_my_notifications(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: UserDetails = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    """Fetch notifications and unread count for current user."""
    items, unread_count, total = await service.get_user_notifications(
        user_id=user.user_id,
        limit=limit,
        offset=offset,
    )
    return NotificationListResponse(
        items=[NotificationItem.model_validate(item) for item in items],
        unread_count=unread_count,
        total=total,
    )


@router.post("/mark-all-read", response_model=SuccessResponse)
async def mark_all_notifications_read(
    user: UserDetails = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> SuccessResponse:
    """Mark all unread notifications for current user as read."""
    count = await service.mark_all_as_read(user_id=user.user_id)
    return SuccessResponse(message=f"Marked {count} notifications as read")
