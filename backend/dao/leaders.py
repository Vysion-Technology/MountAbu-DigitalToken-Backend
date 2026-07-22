from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dbmodels.leader import Leader
from backend.schemas.request.leader import LeaderCreate, LeaderUpdate
from backend.meta import NoticeStatus as LeaderStatus


class LeadersDAO:
    async def create_leader(self, session: AsyncSession, leader: LeaderCreate, created_by: Optional[int], image_path: Optional[str] = None) -> Leader:
        data = leader.model_dump()
        db_obj = Leader(**data, created_by=created_by, image_path=image_path)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get_leader(self, session: AsyncSession, leader_id: int, active_only: bool = False) -> Optional[Leader]:
        stmt = select(Leader).where(Leader.id == leader_id)
        if active_only:
            stmt = stmt.where(Leader.status == LeaderStatus.ACTIVE)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_leaders(self, session: AsyncSession, limit: int = 50, offset: int = 0, active_only: bool = False) -> List[Leader]:
        stmt = select(Leader).order_by(Leader.created_at.desc()).limit(limit).offset(offset)
        if active_only:
            stmt = stmt.where(Leader.status == LeaderStatus.ACTIVE)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update_leader(self, session: AsyncSession, leader_id: int, data: LeaderUpdate) -> Optional[Leader]:
        update_data = data.model_dump(exclude_unset=True)
        stmt = (
            update(Leader).where(Leader.id == leader_id).values(**update_data).returning(Leader)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one_or_none()

    async def delete_leader(self, session: AsyncSession, leader_id: int) -> bool:
        result = await session.execute(delete(Leader).where(Leader.id == leader_id))
        await session.commit()
        return result.rowcount > 0


def get_leaders_dao() -> LeadersDAO:
    return LeadersDAO()
