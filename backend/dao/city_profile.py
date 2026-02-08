from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dbmodels.city_profile import CityProfile
from backend.schemas.request.city_profile import CityProfileCreate, CityProfileUpdate


class CityProfileDAO:
    async def create_city_profile(
        self, session: AsyncSession, profile: CityProfileCreate, user_id: int
    ) -> CityProfile:
        data = profile.model_dump()
        db_obj = CityProfile(**data, created_by_id=user_id)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get_latest_profile(self, session: AsyncSession) -> Optional[CityProfile]:
        result = await session.execute(
            select(CityProfile).order_by(CityProfile.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_profiles(self, session: AsyncSession) -> List[CityProfile]:
        result = await session.execute(select(CityProfile).order_by(CityProfile.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, profile_id: int) -> Optional[CityProfile]:
        result = await session.execute(select(CityProfile).where(CityProfile.id == profile_id))
        return result.scalar_one_or_none()

    async def update_profile(
        self, session: AsyncSession, profile: CityProfileUpdate, user_id: int
    ) -> CityProfile:
        # Instead of modifying existing row, create a new row to maintain history
        return await self.create_city_profile(session, profile, user_id)


# Simple factory used by controllers/services like other DAOs in project
def get_city_profile_dao() -> CityProfileDAO:
    return CityProfileDAO()
