from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dao.base import BaseDAO
from backend.dbmodels.notification import Notification


class NotificationDAO(BaseDAO):
    """Data Access Object for User Notifications."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        application_id: Optional[int] = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            application_id=application_id,
            title=title,
            message=message,
            is_read=False,
            created_at=datetime.now(),
        )
        self.session.add(notification)
        await self.session.commit()
        await self.session.refresh(notification)
        return notification

    async def get_user_notifications(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Notification], int, int]:
        """Fetch notifications, unread count, and total count for a user."""
        # Unread count
        unread_stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        unread_res = await self.session.execute(unread_stmt)
        unread_count = unread_res.scalar() or 0

        # Total count
        total_stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
        )
        total_res = await self.session.execute(total_stmt)
        total = total_res.scalar() or 0

        # List items
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at), desc(Notification.id))
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        items = list(res.scalars().all())

        return items, unread_count, total

    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all unread notifications for a user as read."""
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(
                is_read=True,
                read_at=datetime.now(),
            )
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount or 0
