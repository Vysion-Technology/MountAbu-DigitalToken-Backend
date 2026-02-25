from typing import Optional, Any
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

    async def get_logs(self, session: AsyncSession, skip: int = 0, limit: int = 100):
        logs = await self.dao.get_all(session, skip, limit)
        total = await self.dao.count(session)
        return logs, total
