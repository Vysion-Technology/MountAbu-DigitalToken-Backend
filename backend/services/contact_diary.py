from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dao.contact_diary import ContactDiaryDAO, get_contact_diary_dao
from backend.dbmodels.contact_diary import ContactDiary
from backend.schemas.request.contact_diary import ContactDiaryCreate, ContactDiaryUpdate


class ContactDiaryService:
    def __init__(self, dao: ContactDiaryDAO):
        self.dao = dao

    async def create(
        self, session: AsyncSession, obj_in: ContactDiaryCreate, user_id: int
    ) -> ContactDiary:
        return await self.dao.create(session, obj_in, user_id)

    async def get(self, session: AsyncSession, id: int) -> Optional[ContactDiary]:
        return await self.dao.get(session, id)

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        search: Optional[str] = None,
        designation: Optional[str] = None,
        status: Optional[bool] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[ContactDiary], int]:
        skip = (page - 1) * size
        return await self.dao.get_by_filters(
            session,
            search=search,
            designation=designation,
            status=status,
            skip=skip,
            limit=size,
        )

    async def update(
        self, session: AsyncSession, db_obj: ContactDiary, obj_in: ContactDiaryUpdate
    ) -> ContactDiary:
        return await self.dao.update(session, db_obj, obj_in)

    async def delete(self, session: AsyncSession, id: int) -> Optional[ContactDiary]:
        return await self.dao.remove(session, id)


def get_contact_diary_service() -> ContactDiaryService:
    return ContactDiaryService(get_contact_diary_dao())
