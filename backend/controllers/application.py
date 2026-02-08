from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, Query
from backend.meta import ApplicationDocumentType, ApplicationFlags, UserRole

from backend.middlewares.auth import get_current_user_id, get_current_user
from backend.services.user import UserService, get_user_service
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db

from backend.schemas.base.auth import UserDetails
from backend.schemas.request.application import (
    ApplicationCreate,
    CommentRequest,
    ApplicationMaterialRequirements,
)
from backend.schemas.response.application import ApplicationResponse, CommentResponse
from backend.schemas.response.meta import SuccessResponse, DocumentUploadResponse
from backend.services.application import get_application_service, ApplicationService


router = APIRouter()

# Roles that can access every flag
_ADMIN_ROLES = [UserRole.SUPERADMIN, UserRole.NODAL_OFFICER, UserRole.COMMISSIONER]

# Mapping of flag -> allowed roles that can query with that flag
FLAG_ALLOWED_ROLES: dict[ApplicationFlags, list[UserRole]] = {
    # New Application
    ApplicationFlags.NEW_APPLICATION_REQUIRES_NODAL_OFFICER_ACTION: [*_ADMIN_ROLES, UserRole.NODAL_OFFICER],
    ApplicationFlags.NEW_APPLICATION_REQUIRES_JEN_FIELD_INSPECTION: [*_ADMIN_ROLES, UserRole.JEN],
    ApplicationFlags.NEW_APPLICATION_REQUIRES_JEN_MATERIAL_ENTRY: [*_ADMIN_ROLES, UserRole.JEN],
    ApplicationFlags.NEW_APPLICATION_REQUIRES_NODAL_OFFICER_TOKEN_GENERATION: [*_ADMIN_ROLES, UserRole.NODAL_OFFICER],
    # Renovation
    ApplicationFlags.RENOVATION_REQUIRES_COMMISSIONER_FORWARD: [*_ADMIN_ROLES],
    ApplicationFlags.RENOVATION_REQUIRES_DEPT_COMMENT: [*_ADMIN_ROLES, UserRole.JEN, UserRole.DEPT_ATP, UserRole.DEPT_LAND, UserRole.DEPT_LEGAL],
    ApplicationFlags.RENOVATION_REQUIRES_JEN_FIELD_INSPECTION: [*_ADMIN_ROLES, UserRole.JEN],
    ApplicationFlags.RENOVATION_REQUIRES_JEN_MATERIAL_ENTRY: [*_ADMIN_ROLES, UserRole.JEN],
    ApplicationFlags.RENOVATION_REQUIRES_COMMISSIONER_ACTION: [*_ADMIN_ROLES],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_TOKEN_GENERATION: [*_ADMIN_ROLES, UserRole.NAKA_INCHARGE],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_APPROVAL_PHASE_1: [*_ADMIN_ROLES, UserRole.NAKA_INCHARGE],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_APPROVAL_PHASE_2: [*_ADMIN_ROLES, UserRole.NAKA_INCHARGE],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_APPROVAL_PHASE_3: [*_ADMIN_ROLES, UserRole.NAKA_INCHARGE],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_APPROVAL_PHASE_4: [*_ADMIN_ROLES, UserRole.NAKA_INCHARGE],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_APPROVAL_PHASE_5: [*_ADMIN_ROLES, UserRole.NAKA_INCHARGE],
    ApplicationFlags.RENOVATION_OVERDUE_COMMENTS: [*_ADMIN_ROLES, UserRole.NAKA_INCHARGE],
    ApplicationFlags.RENOVATION_OVERDUE_COMMENTS_JEN: [*_ADMIN_ROLES, UserRole.JEN],
    ApplicationFlags.RENOVATION_OVERDUE_COMMENTS_ATP: [*_ADMIN_ROLES, UserRole.DEPT_ATP],
    ApplicationFlags.RENOVATION_OVERDUE_COMMENTS_LAND: [*_ADMIN_ROLES, UserRole.DEPT_LAND],
    ApplicationFlags.RENOVATION_OVERDUE_COMMENTS_LEGAL: [*_ADMIN_ROLES, UserRole.DEPT_LEGAL],
    # Generic flags
    ApplicationFlags.ALL: [*_ADMIN_ROLES],
    ApplicationFlags.CITIZEN: [UserRole.CITIZEN],
}


@router.post("/applications", response_model=ApplicationResponse)
async def create_application(
    application_create: ApplicationCreate,
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),  # Inject UserService
    db: AsyncSession = Depends(get_db),  # Inject DB session
) -> ApplicationResponse:
    """Create a new application."""
    # Fetch full user to get mobile
    try:
        user = await user_service.get_user_by_id(db, user_id)
        if not user:
            # Should not happen as user_id is from token
            raise HTTPException(status_code=404, detail="User not found")

        return await application_service.create_application(
            application_create, user_id, mobile=user.mobile
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/applications", response_model=List[ApplicationResponse])
async def get_applications(
    flag: ApplicationFlags = Query(..., description="Filter applications by workflow flag"),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    citizen_user_id: Optional[int] = Query(None, description="Citizen user ID (required when flag=CITIZEN)"),
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> List[ApplicationResponse]:
    """Get applications filtered by flag."""
    # Validate role is allowed for the requested flag
    allowed_roles = FLAG_ALLOWED_ROLES.get(flag, [])
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Your role ({user.role.value}) is not permitted to query flag {flag.value}",
        )

    # CITIZEN flag: citizen sees their own applications
    if flag == ApplicationFlags.CITIZEN:
        # Check that the user role is CITIZEN
        if user.role != UserRole.CITIZEN:
            raise HTTPException(
                status_code=400,
                detail="Only users with CITIZEN role can query with CITIZEN flag",
            )
        return await application_service.get_applications(
            flag=None, offset=offset, limit=limit, user_id=user.user_id
        )

    # ALL flag: returns all applications without flag filtering
    if flag == ApplicationFlags.ALL:
        return await application_service.get_applications(
            flag=None, offset=offset, limit=limit,
            user_id=citizen_user_id,  # optionally scope to a specific citizen
        )

    # Workflow flag: filter by computed flag
    return await application_service.get_applications(
        flag=flag, offset=offset, limit=limit
    )


@router.post(
    "/applications/{application_id}/document", response_model=DocumentUploadResponse
)
async def upload_document(
    application_id: int,
    document: UploadFile,
    document_type: ApplicationDocumentType = Form(...),
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
) -> DocumentUploadResponse:
    """Upload a document for an application."""
    try:
        return await application_service.upload_document(
            application_id, document, user_id, document_type
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/applications/{application_id}/materials", response_model=SuccessResponse)
async def add_materials(
    application_id: int,
    materials: List[ApplicationMaterialRequirements],
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Add materials to an existing application."""
    return await application_service.add_application_materials(
        application_id, materials
    )


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
    request_user_data: bool = False,
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> Optional[ApplicationResponse]:
    """Get a specific application by ID."""
    return await application_service.get_application(
        application_id, user, request_user_data
    )


@router.put("/applications/{application_id}/approve", response_model=SuccessResponse)
async def approve_application(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Approve an application. This API shall be called by the NODAL OFFICER."""
    raise NotImplementedError("Approve application logic not implemented yet")


@router.put("/applications/{application_id}/reject", response_model=SuccessResponse)
async def reject_application(
    application_id: int,
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Reject an application. This API shall be called by the NODAL OFFICER."""
    raise NotImplementedError("Reject application logic not implemented yet")


@router.put("/applications/{application_id}/comment", response_model=SuccessResponse)
async def comment_on_application(
    application_id: int,
    comment_request: CommentRequest,
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> SuccessResponse:
    """Add a comment to an application. Any authority or the applicant can comment."""
    # Verify the user is either an authority or the application owner
    if user.role == UserRole.CITIZEN:
        # Citizen can only comment on their own application
        application = await application_service.get_application(application_id, user)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        if application.user_id != user.user_id:
            raise HTTPException(
                status_code=403,
                detail="You can only comment on your own applications",
            )

    return await application_service.comment_on_application(
        application_id, comment_request.comment, user.user_id
    )


@router.get(
    "/applications/{application_id}/comments",
    response_model=List[CommentResponse],
)
async def get_application_comments(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> List[CommentResponse]:
    """Get all comments for an application."""
    comments = await application_service.get_application_comments(application_id)
    return [CommentResponse.model_validate(c) for c in comments]


@router.post("/applications/{application_id}/material", response_model=SuccessResponse)
async def approve_material(
    application_id: int,
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Approve material for an application."""
    raise NotImplementedError("Approve material logic not implemented yet")


@router.delete("/applications/{application_id}", response_model=SuccessResponse)
async def delete_application(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Delete an application."""
    return await application_service.delete_application(application_id)


__all__ = ["router"]
