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
from backend.middlewares.auth import get_current_user, get_optional_user
from backend.schemas.base.auth import UserDetails
from backend.meta import UserRole

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
    current_user: Optional[UserDetails] = Depends(get_optional_user),
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
    
    is_authority = current_user and current_user.role in (
        UserRole.SUPERADMIN,
        UserRole.NODAL_OFFICER,
        UserRole.COMMISSIONER,
        UserRole.ADMIN,
    )

    masked_contacts = []
    for contact in contacts:
        contact_data = ContactDiaryResponse.model_validate(contact)
        if not is_authority:
            # Mask sensitive fields for citizens or unauthenticated users
            contact_data.office_department = "********"
            contact_data.phone_number = "********"
            contact_data.email_address = "********"
            contact_data.created_by = None
        masked_contacts.append(contact_data)

    pages = math.ceil(total / size) if size else 0
    return PaginatedContactDiaryResponse(
        items=masked_contacts, total=total, page=page, size=size, pages=pages
    )


@router.get("/{id}", response_model=ContactDiaryResponse)
async def get_contact_diary(
    id: int,
    session: AsyncSession = Depends(get_db),
    current_user: Optional[UserDetails] = Depends(get_optional_user),
    service: ContactDiaryService = Depends(get_contact_diary_service),
):
    """Get contact diary entry by ID."""
    contact = await service.get(session, id=id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    is_authority = current_user and current_user.role in (
        UserRole.SUPERADMIN,
        UserRole.NODAL_OFFICER,
        UserRole.COMMISSIONER,
        UserRole.ADMIN,
    )

    contact_data = ContactDiaryResponse.model_validate(contact)
    if not is_authority:
        contact_data.office_department = "********"
        contact_data.phone_number = "********"
        contact_data.email_address = "********"
        contact_data.created_by = None

    return contact_data


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
