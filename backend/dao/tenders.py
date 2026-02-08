from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dbmodels.tender import Tender
from backend.schemas.request.tender import TenderCreate, TenderUpdate


class TendersDAO:
    async def create_tender(self, session: AsyncSession, tender: TenderCreate, created_by: Optional[int]) -> Tender:
        data = tender.model_dump()
        db_obj = Tender(**data, created_by=created_by)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get_tender(self, session: AsyncSession, tender_id: int) -> Optional[Tender]:
        result = await session.execute(select(Tender).where(Tender.id == tender_id))
        return result.scalar_one_or_none()

    async def list_tenders(self, session: AsyncSession, limit: int = 50, offset: int = 0) -> List[Tender]:
        result = await session.execute(select(Tender).order_by(Tender.published_on.desc()).limit(limit).offset(offset))
        return result.scalars().all()

    async def update_tender(self, session: AsyncSession, tender_id: int, data: TenderUpdate) -> Optional[Tender]:
        update_data = data.model_dump(exclude_unset=True)
        stmt = (
            update(Tender).where(Tender.id == tender_id).values(**update_data).returning(Tender)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one_or_none()

    async def delete_tender(self, session: AsyncSession, tender_id: int) -> bool:
        result = await session.execute(delete(Tender).where(Tender.id == tender_id))
        await session.commit()
        return result.rowcount > 0


def get_tenders_dao() -> TendersDAO:
    return TendersDAO()
