from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dbmodels.city_profile import CityProfile
from backend.schemas.request.city_profile import CityProfileCreate, CityProfilePut


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
        result = await session.execute(
            select(CityProfile).order_by(CityProfile.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(
        self, session: AsyncSession, profile_id: int
    ) -> Optional[CityProfile]:
        result = await session.execute(
            select(CityProfile).where(CityProfile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def put_profile(
        self,
        session: AsyncSession,
        profile_id: int,
        profile: CityProfilePut,
        user_id: int,
    ) -> Optional[CityProfile]:
        db_obj = await self.get_by_id(session, profile_id)
        if not db_obj:
            return None

        # PUT replaces the entire row by the new content
        update_data = profile.model_dump()
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def patch_profile(
        self,
        session: AsyncSession,
        profile_id: int,
        profile: CityProfileCreate,
        user_id: int,
    ) -> Optional[CityProfile]:
        db_obj = await self.get_by_id(session, profile_id)
        if not db_obj:
            return None

        # PATCH modified an existing row in the database
        update_data = profile.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await session.commit()
        await session.refresh(db_obj)
        return db_obj


# Simple factory used by controllers/services like other DAOs in project
def get_city_profile_dao() -> CityProfileDAO:
    return CityProfileDAO()
