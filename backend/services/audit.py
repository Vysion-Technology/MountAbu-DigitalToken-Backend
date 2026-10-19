from typing import Optional, Any
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dao.audit import AuditLogDAO
from backend.meta.audit import AuditAction
from backend.dbmodels.user import User
from backend.schemas.audit import AuditLogResponse


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

        user_ids = {l.user_id for l in logs if l.user_id}
        users_map = {}
        if user_ids:
            user_stmt = select(User).where(User.id.in_(user_ids))
            user_result = await session.execute(user_stmt)
            users_map = {u.id: u for u in user_result.scalars().all()}

        enriched_logs = []
        for l in logs:
            user = users_map.get(l.user_id)
            user_name = user.name if user else None
            user_role = (
                user.role.value if hasattr(user.role, "value") else str(user.role)
            ) if user and user.role else None

            # Extract record_id from new_state or previous_state
            record_id = None
            state = l.new_state or l.previous_state
            if isinstance(state, dict):
                for key in ("application_id", "token_id", "complaint_id", "user_id", "id"):
                    val = state.get(key)
                    if val is not None and isinstance(val, (int, str)):
                        try:
                            record_id = int(val)
                            break
                        except ValueError:
                            pass

            resp_item = AuditLogResponse(
                id=l.id,
                entity_type=l.entity_type,
                action=l.action,
                user_id=l.user_id,
                previous_state=l.previous_state,
                new_state=l.new_state,
                created_at=l.created_at,
                user_name=user_name,
                user_role=user_role,
                record_id=record_id,
            )
            enriched_logs.append(resp_item)

        return enriched_logs, total
