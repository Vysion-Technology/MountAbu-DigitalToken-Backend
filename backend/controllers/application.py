from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, Query
from backend.meta import (
    ApplicationDocumentType,
    ApplicationFlags,
    UserRole,
    CommentType,
)

from backend.middlewares.auth import get_current_user_id, get_current_user
from backend.services.user import UserService, get_user_service
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db

from backend.schemas.base.auth import UserDetails
from backend.schemas.request.application import (
    ApplicationCreate,
    CommentRequest,
    ApplicationMaterialRequirements,
    WorkflowActionRequest,
    InspectionReportCreate,
    PhaseMaterialEntry,
)
from backend.schemas.response.application import (
    ApplicationResponse,
    CommentResponse,
    PhaseResponse,
    TokenResponse,
    TokenDetailResponse,
)
from backend.schemas.response.meta import SuccessResponse, DocumentUploadResponse
from backend.services.application import get_application_service, ApplicationService
from backend.services.audit import AuditService
from backend.meta.audit import AuditAction

router = APIRouter()
audit_service = AuditService()

# Roles that can access every flag
_ADMIN_ROLES = [UserRole.SUPERADMIN, UserRole.NODAL_OFFICER, UserRole.COMMISSIONER]

# Mapping of flag -> allowed roles that can query with that flag
FLAG_ALLOWED_ROLES: dict[ApplicationFlags, list[UserRole]] = {
    # ── Generic ───────────────────────────────────────────────────────────
    ApplicationFlags.ALL: [*_ADMIN_ROLES],
    ApplicationFlags.CITIZEN: [UserRole.CITIZEN],
    ApplicationFlags.OBJECTED_CITIZEN_ACTION: [*_ADMIN_ROLES, UserRole.CITIZEN],
    # ── New Application ───────────────────────────────────────────────────
    ApplicationFlags.NEW_APPLICATION_REQUIRES_NODAL_OFFICER_ACTION: [*_ADMIN_ROLES],
    ApplicationFlags.NEW_APPLICATION_REQUIRES_JEN_INSPECTION: [
        *_ADMIN_ROLES,
        UserRole.JEN,
    ],
    ApplicationFlags.NEW_APPLICATION_REQUIRES_JEN_FIELD_INSPECTION: [
        *_ADMIN_ROLES,
        UserRole.JEN,
    ],
    ApplicationFlags.NEW_APPLICATION_REQUIRES_JEN_MATERIAL_ENTRY: [
        *_ADMIN_ROLES,
        UserRole.JEN,
    ],
    ApplicationFlags.NEW_APPLICATION_REQUIRES_NODAL_OFFICER_TOKEN_GENERATION: [
        *_ADMIN_ROLES
    ],
    # ── Renovation ────────────────────────────────────────────────────────
    ApplicationFlags.RENOVATION_REQUIRES_COMMISSIONER_FORWARD: [*_ADMIN_ROLES],
    ApplicationFlags.RENOVATION_REQUIRES_DEPT_COMMENT: [
        *_ADMIN_ROLES,
        UserRole.JEN,
        UserRole.DEPT_ATP,
        UserRole.DEPT_LAND,
        UserRole.DEPT_LEGAL,
    ],
    ApplicationFlags.RENOVATION_REQUIRES_JEN_FIELD_INSPECTION: [
        *_ADMIN_ROLES,
        UserRole.JEN,
    ],
    ApplicationFlags.RENOVATION_REQUIRES_JEN_MATERIAL_ENTRY: [
        *_ADMIN_ROLES,
        UserRole.JEN,
    ],
    ApplicationFlags.RENOVATION_REQUIRES_COMMISSIONER_ACTION: [*_ADMIN_ROLES],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_ACTION: [*_ADMIN_ROLES],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_TOKEN_GENERATION: [
        *_ADMIN_ROLES
    ],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_APPROVAL_PHASE_1: [
        *_ADMIN_ROLES
    ],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_APPROVAL_PHASE_2: [
        *_ADMIN_ROLES
    ],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_APPROVAL_PHASE_3: [
        *_ADMIN_ROLES
    ],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_APPROVAL_PHASE_4: [
        *_ADMIN_ROLES
    ],
    ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_APPROVAL_PHASE_5: [
        *_ADMIN_ROLES
    ],
    ApplicationFlags.RENOVATION_OVERDUE_COMMENTS: [*_ADMIN_ROLES],
    ApplicationFlags.RENOVATION_OVERDUE_COMMENTS_JEN: [*_ADMIN_ROLES, UserRole.JEN],
    ApplicationFlags.RENOVATION_OVERDUE_COMMENTS_ATP: [
        *_ADMIN_ROLES,
        UserRole.DEPT_ATP,
    ],
    ApplicationFlags.RENOVATION_OVERDUE_COMMENTS_LAND: [
        *_ADMIN_ROLES,
        UserRole.DEPT_LAND,
    ],
    ApplicationFlags.RENOVATION_OVERDUE_COMMENTS_LEGAL: [
        *_ADMIN_ROLES,
        UserRole.DEPT_LEGAL,
    ],
    # ── Phase & Naka ──────────────────────────────────────────────────────
    ApplicationFlags.PHASE_READY_FOR_NAKA: [*_ADMIN_ROLES],
    ApplicationFlags.NAKA_INCHARGE_ACTION: [*_ADMIN_ROLES],
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

        response = await application_service.create_application(
            application_create, user_id, mobile=user.mobile
        )
        await audit_service.log(
            db,
            "APPLICATION",
            AuditAction.CREATED,
            user_id,
            new_state=response.model_dump(mode="json") if hasattr(response, "model_dump") else None,
        )
        await db.commit()
        return response
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/applications", response_model=List[ApplicationResponse])
async def get_applications(
    flag: ApplicationFlags = Query(
        ..., description="Filter applications by workflow flag"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    citizen_user_id: Optional[int] = Query(
        None, description="Citizen user ID (required when flag=CITIZEN)"
    ),
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> List[ApplicationResponse]:
    """Get applications filtered by flag."""
    if user.role == UserRole.NAKA_INCHARGE:
        raise HTTPException(
            status_code=403,
            detail="NAKA_INCHARGE must use /api/naka/{transport_code} endpoints",
        )
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
            flag=None,
            offset=offset,
            limit=limit,
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


@router.post(
    "/applications/{application_id}/vehicle-entries/{entry_id}/dumping-photo",
    response_model=DocumentUploadResponse,
)
async def upload_dumping_photo(
    application_id: int,
    entry_id: int,
    document: UploadFile,
    application_service: ApplicationService = Depends(get_application_service),
    user_id: int = Depends(get_current_user_id),
) -> DocumentUploadResponse:
    """Upload a dumping photo for a vehicle entry."""
    try:
        return await application_service.upload_dumping_photo(
            application_id, entry_id, document, user_id
        )
    except HTTPException as he:
        raise he
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
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Delete a document from an application."""
    response = await application_service.delete_document(application_id)
    await audit_service.log(
        db,
        "APPLICATION_DOCUMENT",
        AuditAction.CHANGED,
        user_id,
        new_state={"application_id": application_id, "action": "deleted"},
    )
    await db.commit()
    return response


@router.get(
    "/applications/{application_id}", response_model=Optional[ApplicationResponse]
)
async def get_application(
    application_id: int,
    request_user_data: bool = False,
    application_service: ApplicationService = Depends(get_application_service),
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> Optional[ApplicationResponse]:
    """Get a specific application by ID."""
    if user.role == UserRole.NAKA_INCHARGE:
        raise HTTPException(
            status_code=403,
            detail="NAKA_INCHARGE must use /api/naka/{transport_code} endpoints",
        )
    application = await application_service.get_application(
        application_id, user, request_user_data
    )
    if application:
        await audit_service.log(
            db,
            "APPLICATION",
            AuditAction.VIEWED,
            user.user_id,
            new_state={"id": application_id},
        )
        await db.commit()
    return application


@router.put("/applications/{application_id}/submit", response_model=SuccessResponse)
async def submit_application(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> SuccessResponse:
    """Submit an application (PENDING -> SUBMITTED).

    Only the owning CITIZEN can submit. Validates that AADHAAR,
    PERMISSION_DOCUMENTS and OWNERSHIP_DOCUMENTS are attached.
    """
    if user.role != UserRole.CITIZEN:
        raise HTTPException(
            status_code=403,
            detail="Only citizens can submit their applications",
        )
    # Pre-fetch for audit
    prev_app = await application_service.get_application(application_id, user)

    response = await application_service.submit_application(
        application_id, user.user_id
    )

    await audit_service.log(
        db,
        "APPLICATION",
        AuditAction.CHANGED,
        user.user_id,
        previous_state=prev_app.model_dump(mode="json") if prev_app else None,
        new_state={"status": "SUBMITTED"},
    )
    await db.commit()
    return response


@router.post("/applications/{application_id}/withdraw", response_model=SuccessResponse)
async def withdraw_application(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> SuccessResponse:
    """Withdraw an application.

    Only the owning CITIZEN can withdraw.
    Allowed only if status is PENDING or SUBMITTED.
    """
    if user.role != UserRole.CITIZEN:
        raise HTTPException(
            status_code=403,
            detail="Only citizens can withdraw their applications",
        )
    # Pre-fetch for audit
    prev_app = await application_service.get_application(application_id, user)

    response = await application_service.withdraw_application(
        application_id, user.user_id
    )

    await audit_service.log(
        db,
        "APPLICATION",
        AuditAction.CHANGED,
        user.user_id,
        previous_state=prev_app.model_dump(mode="json") if prev_app else None,
        new_state={"status": "WITHDRAWN"},
    )
    await db.commit()
    return response


@router.put("/applications/{application_id}/action", response_model=SuccessResponse)
async def workflow_action(
    application_id: int,
    request: WorkflowActionRequest,
    application_service: ApplicationService = Depends(get_application_service),
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> SuccessResponse:
    """Execute a workflow action on an application.

    Actions: APPROVE, REJECT, OBJECT, FORWARD, GENERATE_TOKENS.
    The state machine validates the transition based on current status,
    application type, and the caller's role.
    """
    # Pre-fetch for audit
    prev_app = await application_service.get_application(application_id, user)

    response = await application_service.perform_workflow_action(
        application_id=application_id,
        request=request,
        user_id=user.user_id,
        user_role=user.role,
    )

    await audit_service.log(
        db,
        "APPLICATION",
        AuditAction.CHANGED,
        user.user_id,
        previous_state=prev_app.model_dump(mode="json") if prev_app else None,
        new_state={"action": request.action, "remarks": request.remarks},
    )
    await db.commit()
    return response


@router.put(
    "/applications/{application_id}/phase-materials", response_model=SuccessResponse
)
async def update_phase_materials(
    application_id: int,
    phase_materials: List[PhaseMaterialEntry],
    application_service: ApplicationService = Depends(get_application_service),
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> SuccessResponse:
    """JEN or SUPERADMIN updates phase materials for an application."""
    if user.role not in (UserRole.JEN, UserRole.SUPERADMIN):
        raise HTTPException(
            status_code=403,
            detail="Only JEN or SUPERADMIN can update phase materials",
        )

    # Pre-fetch for audit
    prev_app = await application_service.get_application(application_id, user)

    response = await application_service.update_phase_materials(
        application_id=application_id,
        phase_materials=phase_materials,
    )

    await audit_service.log(
        db,
        "APPLICATION",
        AuditAction.CHANGED,
        user.user_id,
        previous_state=prev_app.model_dump(mode="json") if prev_app else None,
        new_state={
            "action": "UPDATE_PHASE_MATERIALS",
            "phase_materials": [pm.model_dump(mode="json") for pm in phase_materials],
        },
    )
    await db.commit()
    return response


@router.post(
    "/applications/{application_id}/inspection", response_model=SuccessResponse
)
async def create_inspection(
    application_id: int,
    report: InspectionReportCreate,
    application_service: ApplicationService = Depends(get_application_service),
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> SuccessResponse:
    """JEN creates a site inspection report."""
    if user.role not in (UserRole.JEN, UserRole.SUPERADMIN):
        raise HTTPException(
            status_code=403,
            detail="Only JEN or SUPERADMIN can create inspection reports",
        )
    response = await application_service.create_inspection_report(
        application_id=application_id,
        report=report,
        user_id=user.user_id,
    )
    await audit_service.log(
        db,
        "INSPECTION_REPORT",
        AuditAction.CREATED,
        user.user_id,
        new_state=report.model_dump(mode="json"),
    )
    await db.commit()
    return response


# NOTE: Naka entry creation and listing now uses transport codes.
# See /api/naka/{transport_code} endpoints in controllers/naka.py


@router.get("/applications/{application_id}/phases", response_model=List[PhaseResponse])
async def get_phases(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> List[PhaseResponse]:
    """Get all phases for an application."""
    return await application_service.get_phases(application_id)


@router.put(
    "/applications/{application_id}/phases/{phase}/complete",
    response_model=SuccessResponse,
)
async def complete_phase(
    application_id: int,
    phase: int,
    application_service: ApplicationService = Depends(get_application_service),
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> SuccessResponse:
    """Mark a phase as completed and activate the next one."""
    if user.role not in (UserRole.NODAL_OFFICER, UserRole.SUPERADMIN):
        raise HTTPException(
            status_code=403,
            detail="Only NODAL_OFFICER or SUPERADMIN can complete phases",
        )
    response = await application_service.complete_phase(
        application_id, phase, user.user_id
    )
    await audit_service.log(
        db,
        "APPLICATION_PHASE",
        AuditAction.CHANGED,
        user.user_id,
        new_state={
            "application_id": application_id,
            "phase": phase,
            "action": "completed",
        },
    )
    await db.commit()
    return response


@router.put("/applications/{application_id}/comment", response_model=SuccessResponse)
async def comment_on_application(
    application_id: int,
    comment_request: CommentRequest,
    application_service: ApplicationService = Depends(get_application_service),
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> SuccessResponse:
    """Add a comment to an application. Any authority or the applicant can comment."""
    # Restriction for OBJECTION_COMMENT: Only NODAL_OFFICER and COMMISSIONER can call this type
    if comment_request.comment_type == CommentType.OBJECTION_COMMENT:
        if user.role not in (
            UserRole.NODAL_OFFICER,
            UserRole.COMMISSIONER,
            UserRole.SUPERADMIN,
        ):
            raise HTTPException(
                status_code=403,
                detail="Only NODAL_OFFICER or COMMISSIONER can add objection comments",
            )

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

    response = await application_service.comment_on_application(
        application_id,
        comment_request.comment,
        user.user_id,
        comment_type=comment_request.comment_type,
        media_paths=comment_request.media_paths,
    )
    await audit_service.log(
        db,
        "APPLICATION_COMMENT",
        AuditAction.CREATED,
        user.user_id,
        new_state={
            "application_id": application_id,
            "comment": comment_request.comment,
        },
    )
    await db.commit()
    return response


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


@router.delete("/applications/{application_id}", response_model=SuccessResponse)
async def delete_application(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> SuccessResponse:
    """Delete an application."""
    response = await application_service.delete_application(application_id)
    await audit_service.log(
        db,
        "APPLICATION",
        AuditAction.CHANGED,
        user_id,
        new_state={"id": application_id, "action": "deleted"},
    )
    await db.commit()
    return response


# ── Token endpoints ──────────────────────────────────────────────────────


@router.get("/tokens", response_model=List[TokenResponse])
async def list_tokens(
    status: Optional[str] = Query(
        None, description="Filter by token status: ACTIVE, PENDING, COMPLETED"
    ),
    search: Optional[str] = Query(
        None, description="Search by token number or application number"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> List[TokenResponse]:
    """List tokens (approved application phases) for the current citizen.

    Returns tokens with computed fields:
    - token_number (e.g. TKN-2025-014)
    - application_number (e.g. APP-2025-00321)
    - remaining_quantity_pct (overall remaining material %)
    - valid_till (activation date + 60 days)
    - materials breakdown with approved/consumed/remaining quantities

    Supports filtering by status (ACTIVE, PENDING, COMPLETED) and
    searching by token or application number.
    """
    if user.role not in (
        UserRole.CITIZEN,
        UserRole.SUPERADMIN,
        UserRole.NODAL_OFFICER,
    ):
        raise HTTPException(
            status_code=403,
            detail="Only citizens and admins can list tokens",
        )

    # Filter by user_id only for citizens
    filter_user_id = user.user_id if user.role == UserRole.CITIZEN else None

    return await application_service.get_tokens(
        user_id=filter_user_id,
        status_filter=status,
        search=search,
        offset=offset,
        limit=limit,
    )


@router.get("/applications/{application_id}/tokens", response_model=List[TokenResponse])
async def get_application_tokens(
    application_id: int,
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> List[TokenResponse]:
    """Get all tokens for a specific application with material summaries."""
    if user.role == UserRole.NAKA_INCHARGE:
        raise HTTPException(
            status_code=403,
            detail="NAKA_INCHARGE must use /api/naka/{transport_code} endpoints",
        )
    return await application_service.get_application_tokens(application_id)


@router.get("/tokens/{transport_code}", response_model=TokenDetailResponse)
async def get_token_detail(
    transport_code: str,
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> TokenDetailResponse:
    """Get full token details by transport code.

    Returns everything needed for the Token Detail screen:
    - Token header: token_number, status, valid date range
    - Application info: applicant name, property address, usage, type
    - Authority info: issued by, issued on, token generated from
    - Material summary: per-material approved/consumed/remaining
    - Vehicle entries: all naka checkpoint entries with vehicle, material, qty, date
    """
    if user.role == UserRole.NAKA_INCHARGE:
        raise HTTPException(
            status_code=403,
            detail="NAKA_INCHARGE must use /api/naka/{transport_code} endpoints",
        )
    from backend.core.transport_code import decode_transport_code

    try:
        code_data = decode_transport_code(transport_code)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid or tampered transport code"
        )
    return await application_service.get_token_detail(
        code_data.application_id, code_data.phase
    )


__all__ = ["router"]
