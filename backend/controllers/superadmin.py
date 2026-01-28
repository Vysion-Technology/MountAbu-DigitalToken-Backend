from fastapi import APIRouter

from backend.schemas.request.superadmin import UpdateUserRolesRequest
from backend.schemas.response.auth import LoginSuccessResponse

router = APIRouter()


@router.post("/login", response_model=LoginSuccessResponse)
async def login():
    pass


@router.put("/roles")
async def update_roles(request: UpdateUserRolesRequest):
    pass


__all__ = ["router"]
