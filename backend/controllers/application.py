from backend.schemas.base.auth import UserDetails
from fastapi import Depends
from fastapi import APIRouter
from fastapi import UploadFile

from backend.middlewares.auth import get_current_user_id, get_current_user
from backend.schemas.request.application import ApplicationCreate
from backend.services.application import get_application_service
from backend.services.application import ApplicationService
from backend.schemas.request.application import CommentRequest


router = APIRouter()


@router.post("/applications")
async def create_application(
    application_create: ApplicationCreate,
    application_service: ApplicationService = Depends(get_application_service),
):
    return await application_service.create_application(application_create)


@router.get("/applications")
async def get_applications(
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
    offset: int = 0,
    limit: int = 10,
):
    return await application_service.get_applications(user_id, offset, limit)


@router.post("/applications/{application_id}/document")
async def upload_document(
    application_id: int,
    document: UploadFile,
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
):
    return await application_service.upload_document(application_id, document, user_id)


@router.delete("/applications/{application_id}/document")
async def delete_document(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
):
    return await application_service.delete_document(application_id)


@router.get("/applications/{application_id}")
async def get_application(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
):
    return await application_service.get_application(application_id, user)


@router.put("/applications/{application_id}/approve")
async def approve_application(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
):
    """This API shall be called by the NODAL OFFICER"""
    pass


@router.put("/applications/{application_id}/reject")
async def reject_application(application_id: int):
    """This API shall be called by the NODAL OFFICER"""
    pass


@router.put("/applications/{application_id}/comment")
async def cancel_application(application_id: int, comment_request: CommentRequest):
    """This API can be called by the any authority."""
    pass


@router.post("/applications/{application_id}/material")
async def approve_material(application_id: int):
    pass


@router.delete("/applications/{application_id}")
async def delete_application(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
):
    return await application_service.delete_application(application_id)


__all__ = ["router"]
