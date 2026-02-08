from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dao.city_profile import CityProfileDAO, get_city_profile_dao
from backend.schemas.request.city_profile import CityProfileCreate, CityProfileUpdate


class CityProfileService:
    def __init__(self, dao: CityProfileDAO):
        self.dao = dao

    async def create_profile(self, session: AsyncSession, profile: CityProfileCreate, user_id: int):
        return await self.dao.create_city_profile(session, profile, user_id)

    async def get_latest(self, session: AsyncSession):
        return await self.dao.get_latest_profile(session)

    async def list_history(self, session: AsyncSession):
        return await self.dao.list_profiles(session)

    async def update_profile(self, session: AsyncSession, profile: CityProfileUpdate, user_id: int):
        return await self.dao.update_profile(session, profile, user_id)


async def get_city_profile_service(dao: CityProfileDAO = Depends(get_city_profile_dao)) -> CityProfileService:
    return CityProfileService(dao)
