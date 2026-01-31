from typing import List, Optional

from fastapi import Depends
from fastapi import APIRouter
from fastapi import UploadFile

from backend.middlewares.auth import get_current_user_id, get_current_user
from backend.schemas.base.auth import UserDetails
from backend.schemas.request.application import ApplicationCreate, CommentRequest
from backend.schemas.response.application import ApplicationResponse
from backend.schemas.response.meta import SuccessResponse, DocumentUploadResponse
from backend.services.application import get_application_service, ApplicationService


router = APIRouter()


@router.post("/applications", response_model=ApplicationResponse)
async def create_application(
    application_create: ApplicationCreate,
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
) -> ApplicationResponse:
    """Create a new application."""
    return await application_service.create_application(application_create, user_id)


@router.get("/applications", response_model=List[ApplicationResponse])
async def get_applications(
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
    offset: int = 0,
    limit: int = 10,
) -> List[ApplicationResponse]:
    """Get all applications for the current user."""
    return await application_service.get_applications(user_id, offset, limit)


@router.post(
    "/applications/{application_id}/document", response_model=DocumentUploadResponse
)
async def upload_document(
    application_id: int,
    document: UploadFile,
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
) -> DocumentUploadResponse:
    """Upload a document for an application."""
    return await application_service.upload_document(application_id, document, user_id)


@router.delete(
    "/applications/{application_id}/document", response_model=SuccessResponse
)
async def delete_document(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Delete a document from an application."""
    return await application_service.delete_document(application_id)


@router.get(
    "/applications/{application_id}", response_model=Optional[ApplicationResponse]
)
async def get_application(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> Optional[ApplicationResponse]:
    """Get a specific application by ID."""
    return await application_service.get_application(application_id, user)


@router.put("/applications/{application_id}/approve", response_model=SuccessResponse)
async def approve_application(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Approve an application. This API shall be called by the NODAL OFFICER."""
    pass


@router.put("/applications/{application_id}/reject", response_model=SuccessResponse)
async def reject_application(
    application_id: int,
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Reject an application. This API shall be called by the NODAL OFFICER."""
    pass


@router.put("/applications/{application_id}/comment", response_model=SuccessResponse)
async def cancel_application(
    application_id: int,
    comment_request: CommentRequest,
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Add a comment to an application. This API can be called by any authority."""
    pass


@router.post("/applications/{application_id}/material", response_model=SuccessResponse)
async def approve_material(
    application_id: int,
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Approve material for an application."""
    pass


@router.delete("/applications/{application_id}", response_model=SuccessResponse)
async def delete_application(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Delete an application."""
    return await application_service.delete_application(application_id)


__all__ = ["router"]

