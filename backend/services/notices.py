from typing import Optional
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dao.notices import NoticesDAO, get_notices_dao
from backend.schemas.request.notice import NoticeCreate, NoticeUpdate
from backend.schemas.response.notice import NoticeResponse, NoticesListResponse


class NoticesService:
    def __init__(self, dao: NoticesDAO):
        self.dao = dao

    async def create_notice(self, session: AsyncSession, payload: NoticeCreate, created_by: Optional[int]) -> NoticeResponse:
        db_obj = await self.dao.create_notice(session, payload, created_by)
        return NoticeResponse(
            id=db_obj.id,
            title=db_obj.title,
            notice_type=db_obj.notice_type,
            published_on=db_obj.published_on,
            valid_till=db_obj.valid_till,
            status=db_obj.status,
            visibility=db_obj.visibility,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def get_notice(self, session: AsyncSession, notice_id: int) -> NoticeResponse:
        db_obj = await self.dao.get_notice(session, notice_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Notice not found")
        return NoticeResponse(
            id=db_obj.id,
            title=db_obj.title,
            notice_type=db_obj.notice_type,
            published_on=db_obj.published_on,
            valid_till=db_obj.valid_till,
            status=db_obj.status,
            visibility=db_obj.visibility,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def list_notices(self, session: AsyncSession, limit: int = 50, offset: int = 0) -> NoticesListResponse:
        objs = await self.dao.list_notices(session, limit=limit, offset=offset)
        items = [
            NoticeResponse(
                id=d.id,
                title=d.title,
                notice_type=d.notice_type,
                published_on=d.published_on,
                valid_till=d.valid_till,
                status=d.status,
                visibility=d.visibility,
                created_by=d.created_by,
                created_at=d.created_at,
            )
            for d in objs
        ]
        return NoticesListResponse(notices=items, total=len(items))

    async def update_notice(self, session: AsyncSession, notice_id: int, payload: NoticeUpdate) -> NoticeResponse:
        db_obj = await self.dao.update_notice(session, notice_id, payload)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Notice not found")
        return NoticeResponse(
            id=db_obj.id,
            title=db_obj.title,
            notice_type=db_obj.notice_type,
            published_on=db_obj.published_on,
            valid_till=db_obj.valid_till,
            status=db_obj.status,
            visibility=db_obj.visibility,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def delete_notice(self, session: AsyncSession, notice_id: int) -> bool:
        return await self.dao.delete_notice(session, notice_id)


async def get_notices_service(dao: NoticesDAO = Depends(get_notices_dao)) -> NoticesService:
    return NoticesService(dao)
