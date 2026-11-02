from typing import Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dao.notification import NotificationDAO
from backend.dbmodels.notification import Notification
from backend.services.base import BaseService


class NotificationService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.dao = NotificationDAO(session)

    async def get_user_notifications(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Notification], int, int]:
        return await self.dao.get_user_notifications(user_id, limit=limit, offset=offset)

    async def mark_all_as_read(self, user_id: int) -> int:
        return await self.dao.mark_all_as_read(user_id)

    async def push_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        application_id: int | None = None,
    ) -> Notification:
        return await self.dao.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            application_id=application_id,
        )
