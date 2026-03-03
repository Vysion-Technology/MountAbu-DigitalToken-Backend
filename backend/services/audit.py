from typing import Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dao.audit import AuditLogDAO
from backend.meta.audit import AuditAction


class AuditService:
    def __init__(self):
        self.dao = AuditLogDAO()

    async def log(
        self,
        session: AsyncSession,
        entity_type: str,
        action: AuditAction,
        user_id: int,
        previous_state: Optional[Any] = None,
        new_state: Optional[Any] = None,
    ):
        return await self.dao.create(
            session, entity_type, action, user_id, previous_state, new_state
        )

    async def get_logs(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[int] = None,
        action: Optional[AuditAction] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        logs = await self.dao.get_all(
            session,
            skip,
            limit,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            start_date=start_date,
            end_date=end_date,
        )
        total = await self.dao.count(
            session,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            start_date=start_date,
            end_date=end_date,
        )
        return logs, total
