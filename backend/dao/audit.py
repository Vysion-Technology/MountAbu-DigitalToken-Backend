from typing import List, Optional, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dbmodels.audit_log import AuditLog
from backend.meta.audit import AuditAction


class AuditLogDAO:
    async def create(
        self,
        session: AsyncSession,
        entity_type: str,
        action: AuditAction,
        user_id: int,
        previous_state: Optional[Any] = None,
        new_state: Optional[Any] = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            entity_type=entity_type,
            action=action,
            user_id=user_id,
            previous_state=previous_state,
            new_state=new_state,
        )
        session.add(audit_log)
        await session.flush()
        return audit_log

    async def get_all(
        self, session: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, session: AsyncSession) -> int:
        stmt = select(func.count()).select_from(AuditLog)
        result = await session.execute(stmt)
        return result.scalar_one()
