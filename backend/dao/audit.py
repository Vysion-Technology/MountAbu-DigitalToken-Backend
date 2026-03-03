from typing import List, Optional, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dbmodels.audit_log import AuditLog
from backend.meta.audit import AuditAction
from datetime import datetime


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
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[int] = None,
        action: Optional[AuditAction] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AuditLog]:
        stmt = select(AuditLog)

        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if entity_type is not None:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if start_date is not None:
            stmt = stmt.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(AuditLog.created_at <= end_date)

        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None,
        action: Optional[AuditAction] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        stmt = select(func.count()).select_from(AuditLog)

        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if entity_type is not None:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if start_date is not None:
            stmt = stmt.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(AuditLog.created_at <= end_date)

        result = await session.execute(stmt)
        return result.scalar_one()
