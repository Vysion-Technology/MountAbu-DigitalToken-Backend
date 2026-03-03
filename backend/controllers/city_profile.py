from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.middlewares.auth import get_current_user
from backend.schemas.base.auth import UserDetails
from backend.schemas.request.city_profile import CityProfileCreate, CityProfilePut
from backend.schemas.response.city_profile import CityProfileResponse
from backend.dao.city_profile import get_city_profile_dao, CityProfileDAO

router = APIRouter(prefix="/city-profile", tags=["City Profile"])


@router.post("/", response_model=CityProfileResponse)
async def create_city_profile(
    profile: CityProfileCreate,
    user: UserDetails = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    dao: CityProfileDAO = Depends(get_city_profile_dao),
):
    created = await dao.create_city_profile(session, profile, user.user_id)
    return created


@router.get("/", response_model=CityProfileResponse)
async def get_latest_city_profile(
    session: AsyncSession = Depends(get_db),
    dao: CityProfileDAO = Depends(get_city_profile_dao),
):
    latest = await dao.get_latest_profile(session)
    if not latest:
        raise HTTPException(status_code=404, detail="City profile not found")
    return latest


@router.put("/{profile_id}", response_model=CityProfileResponse)
async def put_city_profile(
    profile_id: int,
    profile: CityProfilePut,
    user: UserDetails = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    dao: CityProfileDAO = Depends(get_city_profile_dao),
):
    updated = await dao.put_profile(session, profile_id, profile, user.user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="City profile not found")
    return updated


@router.patch("/{profile_id}", response_model=CityProfileResponse)
async def patch_city_profile(
    profile_id: int,
    profile: CityProfileCreate,
    user: UserDetails = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    dao: CityProfileDAO = Depends(get_city_profile_dao),
):
    updated = await dao.patch_profile(session, profile_id, profile, user.user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="City profile not found")
    return updated


@router.get("/history", response_model=List[CityProfileResponse])
async def list_profile_history(
    session: AsyncSession = Depends(get_db),
    dao: CityProfileDAO = Depends(get_city_profile_dao),
    user: UserDetails = Depends(get_current_user),
):
    # Guarding history behind authentication; adjust per business requirements
    return await dao.list_profiles(session)
