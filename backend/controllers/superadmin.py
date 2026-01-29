from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_superadmin
from backend.database import get_db
from backend.dbmodels.user import User
from backend.meta import UserRole
from backend.services.user import UserService

router = APIRouter()
user_service = UserService()


class CreateUserRequest(BaseModel):
    mobile: str
    name: str
    role: UserRole
    password: Optional[str] = None
    username: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    user_id: int
    new_password: str

class SetupSuperAdminRequest(BaseModel):
    username: str
    password: str
    mobile: str = "0000000000"


@router.post("/setup")
async def create_initial_superadmin(
    request: SetupSuperAdminRequest, db: AsyncSession = Depends(get_db)
):
    """
    Creates a superadmin if one does not exist (by username).
    Public endpoint for initial setup.
    """
    # Check if ANY superadmin exists? Or just by username?
    # User said: "API that creates superadmin if it already does not exist."
    # I'll check by username for specific account, or I could Count(SuperAdmin).
    # Logic in service check by username.
    await user_service.create_superadmin_if_not_exists(
        db, username=request.username, password=request.password, mobile=request.mobile
    )
    return {"message": "Superadmin setup check complete."}

@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
):
    """
    Superadmin can create new users with some role.
    """
    # Check if user exists
    existing = await user_service.get_user_by_mobile(db, request.mobile)
    if existing:
        raise HTTPException(
            status_code=400, detail="User with this mobile already exists"
        )

    if request.username:
        existing_username = await user_service.get_user_by_username(
            db, request.username
        )
        if existing_username:
            raise HTTPException(
                status_code=400, detail="User with this username already exists"
            )

    new_user = await user_service.create_user(
        db,
        mobile=request.mobile,
        name=request.name,
        role=request.role,
        password=request.password,
        username=request.username,
    )
    await db.commit()
    return {"message": "User created successfully", "user_id": new_user.id}

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
):
    """
    Superadmin can change the password of a user.
    """
    result = await user_service.change_password(
        db, request.user_id, request.new_password
    )
    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Password updated successfully"}
