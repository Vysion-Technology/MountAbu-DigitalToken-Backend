from backend.schemas.base.auth import UserDetails
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func

from backend.database import get_db
from backend.dao.master import MasterDataDAO
from backend.middlewares.auth import (
    get_current_user,
    get_admin_or_nodal,
    get_superadmin,
    get_optional_user,
)
from backend.services.audit import AuditService
from backend.meta.audit import AuditAction

from backend.schemas.request.master import (
    WardCreate,
    WardUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    RoleCreate,
    RoleUpdate,
    ComplaintCategoryCreate,
    ComplaintCategoryUpdate,
    MaterialCreate,
    MaterialUpdate,
)
from backend.schemas.response.master import (
    WardResponse,
    DepartmentResponse,
    RoleResponse,
    ComplaintCategoryResponse,
    MaterialResponse,
    UserSummary,
)

router = APIRouter(prefix="/master", tags=["Master Data"])
dao = MasterDataDAO()
audit_service = AuditService()


# Wards
@router.post("/wards", response_model=WardResponse)
async def create_ward(
    ward: WardCreate,
    current_user: UserDetails = Depends(get_admin_or_nodal),
    session: AsyncSession = Depends(get_db),
):
    response = await dao.create_ward(session, ward, created_by_id=current_user.user_id)
    await audit_service.log(
        session,
        "WARD",
        AuditAction.CREATED,
        current_user.user_id,
        new_state=response.model_dump() if hasattr(response, "model_dump") else None,
    )
    await session.commit()
    return response


@router.get("/wards", response_model=List[WardResponse])
async def list_wards(
    session: AsyncSession = Depends(get_db),
    user: Optional[UserDetails] = Depends(get_optional_user),
):
    active_only = True if not user or user.role != UserRole.SUPERADMIN else False
    return await dao.list_wards(session, active_only=active_only)


@router.put("/wards/{ward_id}", response_model=WardResponse)
async def update_ward(
    ward_id: int,
    ward: WardUpdate,
    current_user: UserDetails = Depends(get_admin_or_nodal),
    session: AsyncSession = Depends(get_db),
):
    updated = await dao.update_ward(session, ward_id, ward)
    if not updated:
        raise HTTPException(status_code=404, detail="Ward not found")

    await audit_service.log(
        session,
        "WARD",
        AuditAction.CHANGED,
        current_user.user_id,
        new_state=updated.model_dump() if hasattr(updated, "model_dump") else None,
    )
    await session.commit()
    return updated


@router.delete("/wards/{ward_id}")
async def delete_ward(
    ward_id: int,
    current_user: UserDetails = Depends(get_admin_or_nodal),
    session: AsyncSession = Depends(get_db),
):
    success = await dao.delete_ward(session, ward_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ward not found")

    await audit_service.log(
        session,
        "WARD",
        AuditAction.DELETED,
        current_user.user_id,
        new_state={"ward_id": ward_id},
    )
    await session.commit()
    return {"message": "Ward deleted successfully"}


from backend.dbmodels.user import User
from backend.meta import UserRole


# Departments
async def _validate_jen_id(session: AsyncSession, jen_id: Optional[int]):
    """Ensure the user exists and has the JEN role."""
    if jen_id is None:
        return
    stmt = select(User).where(User.id == jen_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail=f"User with ID {jen_id} not found")
    if user.role != UserRole.JEN:
        raise HTTPException(
            status_code=400,
            detail=f"User with ID {jen_id} is not a JEN (Role: {user.role})",
        )


@router.post("/departments", response_model=DepartmentResponse)
async def create_department(
    dept: DepartmentCreate,
    current_user: UserDetails = Depends(get_admin_or_nodal),
    session: AsyncSession = Depends(get_db),
):
    await _validate_jen_id(session, dept.jen_id)
    response = await dao.create_department(
        session, dept, created_by_id=current_user.user_id
    )
    await audit_service.log(
        session,
        "DEPARTMENT",
        AuditAction.CREATED,
        current_user.user_id,
        new_state=response.model_dump() if hasattr(response, "model_dump") else None,
    )
    await session.commit()
    return response


@router.get("/departments", response_model=List[DepartmentResponse])
async def list_departments(
    session: AsyncSession = Depends(get_db),
    user: Optional[UserDetails] = Depends(get_optional_user),
):
    active_only = True if not user or user.role != UserRole.SUPERADMIN else False
    return await dao.list_departments(session, active_only=active_only)


@router.put("/departments/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: int,
    dept: DepartmentUpdate,
    current_user: UserDetails = Depends(get_admin_or_nodal),
    session: AsyncSession = Depends(get_db),
):
    await _validate_jen_id(session, dept.jen_id)
    updated = await dao.update_department(session, dept_id, dept)
    if not updated:
        raise HTTPException(status_code=404, detail="Department not found")

    await audit_service.log(
        session,
        "DEPARTMENT",
        AuditAction.CHANGED,
        current_user.user_id,
        new_state=updated.model_dump() if hasattr(updated, "model_dump") else None,
    )
    await session.commit()
    return updated


@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: int,
    current_user: UserDetails = Depends(get_admin_or_nodal),
    session: AsyncSession = Depends(get_db),
):
    success = await dao.delete_department(session, dept_id)
    if not success:
        raise HTTPException(status_code=404, detail="Department not found")

    await audit_service.log(
        session,
        "DEPARTMENT",
        AuditAction.DELETED,
        current_user.user_id,
        new_state={"dept_id": dept_id},
    )
    await session.commit()
    return {"message": "Department deleted successfully"}


# Roles
@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role: RoleCreate,
    current_user: UserDetails = Depends(get_superadmin),
    session: AsyncSession = Depends(get_db),
):
    return await dao.create_role(session, role, created_by_id=current_user.user_id)


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    session: AsyncSession = Depends(get_db),
    user: Optional[UserDetails] = Depends(get_optional_user),
):
    active_only = True if not user or user.role != UserRole.SUPERADMIN else False
    return await dao.list_roles(session, active_only=active_only)


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role: RoleUpdate,
    current_user: UserDetails = Depends(get_superadmin),
    session: AsyncSession = Depends(get_db),
):
    updated = await dao.update_role(session, role_id, role)
    if not updated:
        raise HTTPException(status_code=404, detail="Role not found")
    return updated


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user: UserDetails = Depends(get_superadmin),
    session: AsyncSession = Depends(get_db),
):
    success = await dao.delete_role(session, role_id)
    if not success:
        raise HTTPException(status_code=404, detail="Role not found")
    await session.commit()
    return {"message": "Role deleted successfully"}


# Complaint Categories
@router.post("/complaint-categories", response_model=ComplaintCategoryResponse)
async def create_complaint_category(
    category: ComplaintCategoryCreate,
    current_user: UserDetails = Depends(get_admin_or_nodal),
    session: AsyncSession = Depends(get_db),
):
    return await dao.create_complaint_category(
        session, category, created_by_id=current_user.user_id
    )


@router.get("/complaint-categories", response_model=List[ComplaintCategoryResponse])
async def list_complaint_categories(
    session: AsyncSession = Depends(get_db),
    user: Optional[UserDetails] = Depends(get_optional_user),
):
    active_only = True if not user or user.role != UserRole.SUPERADMIN else False
    return await dao.list_complaint_categories(session, active_only=active_only)


@router.put(
    "/complaint-categories/{category_id}", response_model=ComplaintCategoryResponse
)
async def update_complaint_category(
    category_id: int,
    category: ComplaintCategoryUpdate,
    current_user: UserDetails = Depends(get_admin_or_nodal),
    session: AsyncSession = Depends(get_db),
):
    updated = await dao.update_complaint_category(session, category_id, category)
    if not updated:
        raise HTTPException(status_code=404, detail="Category not found")
    return updated


@router.delete("/complaint-categories/{category_id}")
async def delete_complaint_category(
    category_id: int,
    current_user: UserDetails = Depends(get_admin_or_nodal),
    session: AsyncSession = Depends(get_db),
):
    success = await dao.delete_complaint_category(session, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    await session.commit()
    return {"message": "Category deleted successfully"}


# Materials
@router.post("/materials", response_model=MaterialResponse)
async def create_material(
    material: MaterialCreate,
    current_user: UserDetails = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await dao.create_material(
        session, material, created_by_id=current_user.user_id
    )


@router.get("/materials", response_model=List[MaterialResponse])
async def list_materials(
    session: AsyncSession = Depends(get_db),
    user: Optional[UserDetails] = Depends(get_optional_user),
):
    active_only = True if not user or user.role != UserRole.SUPERADMIN else False
    return await dao.list_materials(session)


@router.put("/materials/{material_id}", response_model=MaterialResponse)
async def update_material(
    material_id: int,
    material: MaterialUpdate,
    current_user: UserDetails = Depends(get_admin_or_nodal),
    session: AsyncSession = Depends(get_db),
):
    updated = await dao.update_material(session, material_id, material)
    if not updated:
        raise HTTPException(status_code=404, detail="Material not found")

    await audit_service.log(
        session,
        "MATERIAL",
        AuditAction.CHANGED,
        current_user.user_id,
        new_state=updated.model_dump() if hasattr(updated, "model_dump") else None,
    )
    await session.commit()
    return updated


@router.delete("/materials/{material_id}")
async def delete_material(
    material_id: int,
    current_user: UserDetails = Depends(get_admin_or_nodal),
    session: AsyncSession = Depends(get_db),
):
    success = await dao.delete_material(session, material_id)
    if not success:
        raise HTTPException(status_code=404, detail="Material not found")

    await audit_service.log(
        session,
        "MATERIAL",
        AuditAction.DELETED,
        current_user.user_id,
        new_state={"material_id": material_id},
    )
    await session.commit()
    return {"message": "Material deleted successfully"}


# Users / Officials
@router.get("/jens", response_model=List[UserSummary])
async def list_jens(
    current_user: UserDetails = Depends(get_superadmin),
    session: AsyncSession = Depends(get_db),
):
    """List all users with the JEN role. Only accessible by superadmin."""
    stmt = select(User).where(User.role == UserRole.JEN).order_by(User.name)
    result = await session.execute(stmt)
    return result.scalars().all()
