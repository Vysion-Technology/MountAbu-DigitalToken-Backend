from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from backend.config import settings
from backend.meta import UserRole
from backend.schemas.base.auth import UserDetails

# HTTPBearer scheme - expects token in "Authorization: Bearer <token>" header
# Shows simple token input in Swagger UI
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserDetails:
    """Get user details from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials for user",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id_str: str = payload.get("sub")
        role_str: str = payload.get("role")

        if user_id_str is None:
            raise credentials_exception

        user_id = int(user_id_str)
        role = UserRole(role_str) if role_str else UserRole.CITIZEN

    except (JWTError, ValueError):
        raise credentials_exception

    return UserDetails(user_id=user_id, role=role)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """Get user id from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials for user id",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id_str: str = payload.get("sub")

        if user_id_str is None:
            raise credentials_exception

        return int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception


async def get_superadmin(
    current_user: UserDetails = Depends(get_current_user),
) -> UserDetails:
    """Verify that the current user is a superadmin."""
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can access this resource",
        )
    return current_user


async def get_admin_or_nodal(
    current_user: UserDetails = Depends(get_current_user),
) -> UserDetails:
    """Verify that the current user is a superadmin or nodal officer."""
    if current_user.role not in (UserRole.SUPERADMIN, UserRole.NODAL_OFFICER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins or nodal officers can access this resource",
        )
    return current_user


async def get_audit_viewer(
    current_user: UserDetails = Depends(get_current_user),
) -> UserDetails:
    """Verify that the current user can view audit logs."""
    if current_user.role not in (
        UserRole.ADMIN,
        UserRole.SUPERADMIN,
        UserRole.NODAL_OFFICER,
        UserRole.COMMISSIONER,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, Superadmin, Nodal Officers, or Commissioner can view audit logs",
        )
    return current_user
