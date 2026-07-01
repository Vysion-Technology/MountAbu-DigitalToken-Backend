from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.middlewares.auth import get_superadmin
from backend.database import get_db
from backend.schemas.base.auth import UserDetails
from backend.meta import UserRole
from backend.schemas.response.meta import MessageResponse, UserCreatedResponse
from backend.services.user import UserService
from backend.core.security import decrypt_and_verify_payload

router = APIRouter()
user_service = UserService()


class CreateUserRequest(BaseModel):
    """Request schema for creating a new user."""

    mobile: str = Field(..., min_length=10, max_length=10, pattern=r"^[0-9]+$", description="User's 10-digit mobile number")
    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    role: UserRole = Field(..., description="User's role in the system")
    password: Optional[str] = Field(None, description="Optional password for the user")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Optional username for the user")


class UpdateUserRequest(BaseModel):
    """Request schema for updating user details."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated full name")
    mobile: Optional[str] = Field(None, min_length=10, max_length=10, pattern=r"^[0-9]+$", description="Updated 10-digit mobile number")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Updated username")
    is_active: Optional[bool] = Field(None, description="Status of the user (active or not)")


class ChangePasswordRequest(BaseModel):
    """Request schema for changing a user's password."""

    user_id: int = Field(
        ..., description="ID of the user whose password will be changed"
    )
    new_password: str = Field(..., description="New password for the user")


class SetupSuperAdminRequest(BaseModel):
    """Request schema for initial superadmin setup."""

    username: str = Field(..., description="Username for the superadmin")
    password: str = Field(..., description="Password for the superadmin")
    mobile: str = Field("0000000000", min_length=10, max_length=10, pattern=r"^[0-9]+$", description="Mobile number for the superadmin")


@router.post("/setup", response_model=MessageResponse)
async def create_initial_superadmin(
    request: SetupSuperAdminRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Creates a superadmin if one does not exist (by username).
    Public endpoint for initial setup.
    """
    username, _ = decrypt_and_verify_payload(request.username)
    password, _ = decrypt_and_verify_payload(request.password)
    
    await user_service.create_superadmin_if_not_exists(
        db, username=username, password=password, mobile=request.mobile
    )
    return MessageResponse(message="Superadmin setup check complete.")


@router.post(
    "/users", status_code=status.HTTP_201_CREATED, response_model=UserCreatedResponse
)
async def create_user(
    request: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_superadmin),
) -> UserCreatedResponse:
    """
    Superadmin can create new users with some role.
    """
    # Decrypt sensitive fields
    username, _ = decrypt_and_verify_payload(request.username) if request.username else (None, None)
    password, _ = decrypt_and_verify_payload(request.password) if request.password else (None, None)

    existing = await user_service.get_user_by_mobile(db, request.mobile)
    if existing:
        raise HTTPException(
            status_code=400, detail="User with this mobile already exists"
        )

    if username:
        existing_username = await user_service.get_user_by_username(
            db, username
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
        password=password,
        username=username,
    )
    await db.commit()
    return UserCreatedResponse(message="User created successfully", user_id=new_user.id)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_superadmin),
) -> MessageResponse:
    """
    Superadmin can change the password of a user.
    """
    password, _ = decrypt_and_verify_payload(request.new_password)
    result = await user_service.change_password(
        db, request.user_id, password
    )
    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return MessageResponse(message="Password updated successfully")


@router.put("/users/{user_id}", response_model=MessageResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_superadmin),
) -> MessageResponse:
    """
    Superadmin can update user details like name, mobile, username, or status.
    """
    # 1. Check if user exists
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. If mobile is being updated, check for uniqueness
    if request.mobile and request.mobile != user.mobile:
        existing = await user_service.get_user_by_mobile(db, request.mobile)
        if existing:
            raise HTTPException(
                status_code=400, detail="User with this mobile already exists"
            )

    # 3. If username is being updated, check for uniqueness
    if request.username and request.username != user.username:
        existing_username = await user_service.get_user_by_username(
            db, request.username
        )
        if existing_username:
            raise HTTPException(
                status_code=400, detail="User with this username already exists"
            )

    # 4. Perform update
    await user_service.update_user(
        db,
        user_id=user_id,
        name=request.name,
        mobile=request.mobile,
        username=request.username,
        is_active=request.is_active,
    )
    await db.commit()

    return MessageResponse(message="User details updated successfully")


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_superadmin),
) -> MessageResponse:
    """
    Superadmin can hard-delete a user.
    Note: This will fail if the user has associated records (applications, etc.)
    due to foreign key constraints.
    """
    try:
        success = await user_service.hard_delete_user(db, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        await db.commit()
    except Exception as e:
        await db.rollback()
        # Check if it's a foreign key constraint error (simplified check)
        error_msg = str(e)
        if "foreign key" in error_msg.lower() or "violates" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Cannot delete user: Associated records exist (applications, complaints, etc.). Deactivate the user instead.",
            )
        # Global handler will mask this if debug=False
        raise e

    return MessageResponse(message="User deleted successfully")
