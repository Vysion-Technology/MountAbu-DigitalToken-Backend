from typing import List, Optional, Tuple
from pydantic import BaseModel
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dbmodels.contact_diary import ContactDiary
from backend.schemas.request.contact_diary import ContactDiaryCreate


class ContactDiaryDAO:
    async def create(
        self, session: AsyncSession, obj_in: ContactDiaryCreate, user_id: int
    ) -> ContactDiary:
        data = obj_in.model_dump()
        data["created_by"] = user_id
        db_obj = ContactDiary(**data)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get(self, session: AsyncSession, id: int) -> Optional[ContactDiary]:
        result = await session.execute(
            select(ContactDiary).where(ContactDiary.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_filters(
        self,
        session: AsyncSession,
        *,
        search: Optional[str] = None,
        designation: Optional[str] = None,
        status: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ContactDiary], int]:
        query = select(ContactDiary)

        filters = []
        if search:
            filters.append(
                or_(
                    ContactDiary.contact_person.ilike(f"%{search}%"),
                    ContactDiary.office_department.ilike(f"%{search}%"),
                    ContactDiary.email_address.ilike(f"%{search}%"),
                    ContactDiary.phone_number.ilike(f"%{search}%"),
                )
            )
        if designation:
            filters.append(ContactDiary.designation == designation)
        if status is not None:
            filters.append(ContactDiary.status == status)

        if filters:
            query = query.where(*filters)

        # Total count
        count_result = await session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Paginated items
        result = await session.execute(
            query.order_by(ContactDiary.created_at.desc()).offset(skip).limit(limit)
        )
        items = list(result.scalars().all())

        return items, total

    async def update(
        self, session: AsyncSession, db_obj: ContactDiary, obj_in: BaseModel
    ) -> ContactDiary:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def remove(self, session: AsyncSession, id: int) -> Optional[ContactDiary]:
        db_obj = await self.get(session, id)
        if db_obj:
            await session.delete(db_obj)
            await session.commit()
        return db_obj


def get_contact_diary_dao() -> ContactDiaryDAO:
    return ContactDiaryDAO()
