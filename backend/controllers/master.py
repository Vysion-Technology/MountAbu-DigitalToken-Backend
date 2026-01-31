from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dao.master import MasterDataDAO
from backend.middlewares.auth import get_current_user
from backend.dbmodels.user import User

from backend.schemas.request.master import (
    WardCreate,
    WardUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    RoleCreate,
    RoleUpdate,
    ComplaintCategoryCreate,
    ComplaintCategoryUpdate,
)
from backend.schemas.response.master import (
    WardResponse,
    DepartmentResponse,
    RoleResponse,
    ComplaintCategoryResponse,
)

router = APIRouter(prefix="/master", tags=["Master Data"])
dao = MasterDataDAO()


# Wards
@router.post("/wards", response_model=WardResponse)
async def create_ward(
    ward: WardCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await dao.create_ward(session, ward)


@router.get("/wards", response_model=List[WardResponse])
async def list_wards(session: AsyncSession = Depends(get_db)):
    return await dao.list_wards(session)


@router.put("/wards/{ward_id}", response_model=WardResponse)
async def update_ward(
    ward_id: int,
    ward: WardUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    updated = await dao.update_ward(session, ward_id, ward)
    if not updated:
        raise HTTPException(status_code=404, detail="Ward not found")
    return updated


# Departments
@router.post("/departments", response_model=DepartmentResponse)
async def create_department(
    dept: DepartmentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await dao.create_department(session, dept)


@router.get("/departments", response_model=List[DepartmentResponse])
async def list_departments(session: AsyncSession = Depends(get_db)):
    return await dao.list_departments(session)


@router.put("/departments/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: int,
    dept: DepartmentUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    updated = await dao.update_department(session, dept_id, dept)
    if not updated:
        raise HTTPException(status_code=404, detail="Department not found")
    return updated


# Roles
@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role: RoleCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await dao.create_role(session, role)


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(session: AsyncSession = Depends(get_db)):
    return await dao.list_roles(session)


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role: RoleUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    updated = await dao.update_role(session, role_id, role)
    if not updated:
        raise HTTPException(status_code=404, detail="Role not found")
    return updated


# Complaint Categories
@router.post("/complaint-categories", response_model=ComplaintCategoryResponse)
async def create_complaint_category(
    category: ComplaintCategoryCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await dao.create_complaint_category(session, category)


@router.get("/complaint-categories", response_model=List[ComplaintCategoryResponse])
async def list_complaint_categories(session: AsyncSession = Depends(get_db)):
    return await dao.list_complaint_categories(session)


@router.put(
    "/complaint-categories/{category_id}", response_model=ComplaintCategoryResponse
)
async def update_complaint_category(
    category_id: int,
    category: ComplaintCategoryUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    updated = await dao.update_complaint_category(session, category_id, category)
    if not updated:
        raise HTTPException(status_code=404, detail="Category not found")
    return updated
