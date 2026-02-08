from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dbmodels.notice import Notice
from backend.schemas.request.notice import NoticeCreate, NoticeUpdate


class NoticesDAO:
    async def create_notice(self, session: AsyncSession, notice: NoticeCreate, created_by: Optional[int]) -> Notice:
        data = notice.model_dump()
        db_obj = Notice(**data, created_by=created_by)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get_notice(self, session: AsyncSession, notice_id: int) -> Optional[Notice]:
        result = await session.execute(select(Notice).where(Notice.id == notice_id))
        return result.scalar_one_or_none()

    async def list_notices(self, session: AsyncSession, limit: int = 50, offset: int = 0) -> List[Notice]:
        result = await session.execute(select(Notice).order_by(Notice.published_on.desc()).limit(limit).offset(offset))
        return result.scalars().all()

    async def update_notice(self, session: AsyncSession, notice_id: int, data: NoticeUpdate) -> Optional[Notice]:
        update_data = data.model_dump(exclude_unset=True)
        stmt = (
            update(Notice).where(Notice.id == notice_id).values(**update_data).returning(Notice)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one_or_none()

    async def delete_notice(self, session: AsyncSession, notice_id: int) -> bool:
        result = await session.execute(delete(Notice).where(Notice.id == notice_id))
        await session.commit()
        return result.rowcount > 0


def get_notices_dao() -> NoticesDAO:
    return NoticesDAO()
