import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.contact_diary import (
    ContactDiaryService,
    get_contact_diary_service,
)
from backend.schemas.request.contact_diary import (
    ContactDiaryCreate,
    ContactDiaryUpdate,
    ContactDiaryPut,
)
from backend.schemas.response.contact_diary import (
    ContactDiaryResponse,
    PaginatedContactDiaryResponse,
)
from backend.middlewares.auth import get_current_user
from backend.schemas.base.auth import UserDetails

router = APIRouter()


@router.post("/", response_model=ContactDiaryResponse)
async def create_contact_diary(
    contact_in: ContactDiaryCreate,
    session: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_current_user),
    service: ContactDiaryService = Depends(get_contact_diary_service),
):
    """Create new contact diary entry."""
    return await service.create(
        session, obj_in=contact_in, user_id=current_user.user_id
    )


@router.get("/", response_model=PaginatedContactDiaryResponse)
async def get_contact_diaries(
    session: AsyncSession = Depends(get_db),
    search: Optional[str] = None,
    designation: Optional[str] = None,
    status: Optional[bool] = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: UserDetails = Depends(get_current_user),
    service: ContactDiaryService = Depends(get_contact_diary_service),
):
    """Retrieve contact diary entries."""
    contacts, total = await service.get_multi(
        session,
        search=search,
        designation=designation,
        status=status,
        page=page,
        size=size,
    )
    pages = math.ceil(total / size) if size else 0
    return PaginatedContactDiaryResponse(
        items=contacts, total=total, page=page, size=size, pages=pages
    )


@router.get("/{id}", response_model=ContactDiaryResponse)
async def get_contact_diary(
    id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_current_user),
    service: ContactDiaryService = Depends(get_contact_diary_service),
):
    """Get contact diary entry by ID."""
    contact = await service.get(session, id=id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/{id}", response_model=ContactDiaryResponse)
async def update_contact_diary(
    id: int,
    contact_in: ContactDiaryPut,
    session: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_current_user),
    service: ContactDiaryService = Depends(get_contact_diary_service),
):
    """Update a contact diary entry."""
    contact = await service.get(session, id=id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return await service.update(session, db_obj=contact, obj_in=contact_in)


@router.patch("/{id}", response_model=ContactDiaryResponse)
async def patch_contact_diary(
    id: int,
    contact_in: ContactDiaryUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_current_user),
    service: ContactDiaryService = Depends(get_contact_diary_service),
):
    """Patch a contact diary entry (partial update)."""
    contact = await service.get(session, id=id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return await service.update(session, db_obj=contact, obj_in=contact_in)


@router.delete("/{id}", response_model=ContactDiaryResponse)
async def delete_contact_diary(
    id: int,
    session: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_current_user),
    service: ContactDiaryService = Depends(get_contact_diary_service),
):
    """Delete a contact diary entry."""
    contact = await service.get(session, id=id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return await service.delete(session, id=id)
