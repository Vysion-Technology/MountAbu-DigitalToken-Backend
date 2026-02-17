from typing import List, Optional

from fastapi import Depends, UploadFile

from backend.dao.application import get_application_dao, ApplicationDAO
from backend.dao.applicationmaterial import (
    ApplicationMaterialDAO,
    get_application_material_dao,
)
from backend.meta import (
    ApplicationDocumentType,
    ApplicationFlags,
    CommentType,
    UserRole,
)
from backend.schemas.base.auth import UserDetails
from backend.schemas.request.application import (
    ApplicationCreate,
    ApplicationMaterialCreate,
    ApplicationMaterialRequirements,
    InspectionReportCreate,
    NakaEntryCreate,
    WorkflowActionRequest,
)
from backend.schemas.response.application import (
    ApplicationResponse,
    PhaseResponse,
    TokenResponse,
    TokenDetailResponse,
)
from backend.schemas.response.meta import SuccessResponse, DocumentUploadResponse
from backend.services.base import BaseService
from backend.services.storage import get_storage_service


class ApplicationService(BaseService):
    """Application service for handling application business logic."""

    def __init__(self, dao: ApplicationDAO):
        self.dao = dao

    async def create_application(
        self, application: ApplicationCreate, user_id: int, mobile: str
    ) -> ApplicationResponse:
        """Create a new application."""
        return await self.dao.create_application(application, user_id, mobile)

    async def get_application(
        self, application_id: int, user: UserDetails, request_user_data: bool = False
    ) -> Optional[ApplicationResponse]:
        """Get a specific application by ID."""
        if request_user_data:
            print(
                f"User {user.user_id} requested full user data for application {application_id}"
            )

        application = await self.dao.get_application(application_id)

        if application and user.role == UserRole.NAKA_INCHARGE:
            # Sanitize user details for NAKA_INCHARGE
            application.mobile = "******"
            application.email = "******"
            application.current_address = "******"

        return application

    async def get_applications(
        self,
        flag: Optional[ApplicationFlags],
        offset: int,
        limit: int,
        user_id: Optional[int] = None,
    ) -> List[ApplicationResponse]:
        """Get applications filtered by flag with pagination."""
        return await self.dao.get_applications(
            flag=flag, offset=offset, limit=limit, user_id=user_id
        )

    async def delete_application(self, application_id: int) -> SuccessResponse:
        """Delete an application by ID."""
        return await self.dao.delete_application(application_id)

    async def comment_on_application(
        self,
        application_id: int,
        comment: str,
        user_id: int,
        comment_type: CommentType = CommentType.GENERAL,
        media_paths: Optional[list] = None,
    ) -> SuccessResponse:
        """Add a comment to an application."""
        return await self.dao.comment_on_application(
            application_id, comment, user_id, comment_type, media_paths
        )

    async def get_application_comments(self, application_id: int) -> list:
        """Get comments for an application."""
        return await self.dao.get_comments(application_id)

    async def upload_document(
        self,
        application_id: int,
        document: UploadFile,
        user_id: int,
        document_type: ApplicationDocumentType = ApplicationDocumentType.OTHER,
    ) -> DocumentUploadResponse:
        """Upload and save document for an application."""
        storage = get_storage_service()
        if not storage:
            raise Exception("Storage service unavailable")

        file_path = f"applications/{application_id}/{document.filename}"
        path = await storage.upload_file(document, file_path)

        await self.dao.add_document(
            application_id=application_id,
            document_path=path,
            document_type=document_type,
            user_id=user_id,
            document_name=document.filename,
        )
        return DocumentUploadResponse(
            message="Document uploaded successfully", path=path
        )

    async def delete_document(
        self, application_id: int, document_id: Optional[int] = None
    ) -> SuccessResponse:
        """Delete a document from an application."""
        return SuccessResponse(message=None)

    async def submit_application(
        self, application_id: int, user_id: int
    ) -> SuccessResponse:
        """Submit an application (PENDING -> SUBMITTED) with document validation."""
        return await self.dao.submit_application(application_id, user_id)

    async def update_application(
        self, application_id: int, application: ApplicationCreate
    ) -> Optional[ApplicationResponse]:
        """Update an application."""
        return await self.dao.update_application(application_id, application)

    async def add_application_materials(
        self,
        application_id: int,
        material_requirements: list[ApplicationMaterialRequirements],
    ) -> SuccessResponse:
        """Add materials to an existing application."""
        return await self.dao.add_materials(application_id, material_requirements)

    # ── Workflow action ───────────────────────────────────────────────────
    async def perform_workflow_action(
        self,
        application_id: int,
        request: WorkflowActionRequest,
        user_id: int,
        user_role: UserRole,
    ) -> SuccessResponse:
        """Execute a workflow action (approve/reject/object/forward/generate-tokens)."""
        return await self.dao.perform_workflow_action(
            application_id=application_id,
            action=request.action,
            user_id=user_id,
            user_role=user_role,
            remarks=request.remarks,
            num_stages=request.num_stages,
            phase_materials=request.phase_materials,
        )

    # ── JEN inspection ────────────────────────────────────────────────────
    async def create_inspection_report(
        self,
        application_id: int,
        report: InspectionReportCreate,
        user_id: int,
    ) -> SuccessResponse:
        """Create an inspection report."""
        return await self.dao.create_inspection_report(
            application_id=application_id,
            user_id=user_id,
            latitude=report.latitude,
            longitude=report.longitude,
            remarks=report.remarks,
            media_paths=report.media_paths,
            recommended_phases=report.recommended_phases,
            phase_materials=report.phase_materials,
        )

    # ── Naka entry ────────────────────────────────────────────────────────
    async def create_naka_entry(
        self,
        application_id: int,
        phase: int,
        entry: NakaEntryCreate,
        user_id: int,
    ) -> SuccessResponse:
        """Log a naka checkpoint entry."""
        return await self.dao.create_naka_entry(
            application_id=application_id,
            phase=phase,
            user_id=user_id,
            material_id=entry.material_id,
            quantity_brought=entry.quantity_brought,
            vehicle_number=entry.vehicle_number,
            remarks=entry.remarks,
            media_path=entry.media_path,
        )

    async def get_naka_entries(self, application_id: int) -> list:
        """Get all naka entries for an application."""
        from backend.schemas.response.application import NakaEntryResponse

        entries = await self.dao.get_naka_entries(application_id)
        return [NakaEntryResponse.model_validate(e) for e in entries]

    async def get_phase_material_summary(self, application_id: int, phase: int) -> dict:
        """Get material summary for a phase (used by naka checkpoint)."""
        return await self.dao.get_phase_material_summary(application_id, phase)

    # ── Phase management ──────────────────────────────────────────────────
    async def get_phases(self, application_id: int) -> list[PhaseResponse]:
        """Get phases for an application."""
        phases = await self.dao.get_phases(application_id)
        return [PhaseResponse.model_validate(p) for p in phases]

    async def complete_phase(
        self, application_id: int, phase: int, user_id: int
    ) -> SuccessResponse:
        """Mark a phase as completed."""
        return await self.dao.complete_phase(application_id, phase, user_id)

    # ── Token queries ─────────────────────────────────────────────────────
    async def get_citizen_tokens(
        self,
        user_id: int,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 10,
    ) -> list[TokenResponse]:
        """Get all tokens for a citizen with optional filters."""
        token_dicts = await self.dao.get_citizen_tokens(
            user_id=user_id,
            status_filter=status_filter,
            search=search,
            offset=offset,
            limit=limit,
        )
        return [TokenResponse.model_validate(t) for t in token_dicts]

    async def get_application_tokens(self, application_id: int) -> list[TokenResponse]:
        """Get all tokens for a specific application."""
        token_dicts = await self.dao.get_application_tokens(application_id)
        return [TokenResponse.model_validate(t) for t in token_dicts]

    async def get_token_detail(
        self, application_id: int, phase: int
    ) -> TokenDetailResponse:
        """Get full token detail for a single phase (by decoded transport code)."""
        detail_dict = await self.dao.get_token_detail(application_id, phase)
        return TokenDetailResponse.model_validate(detail_dict)


class ApplicationMaterialService(BaseService):
    """Service for handling application material operations."""

    def __init__(self, dao: ApplicationMaterialDAO):
        self.dao: ApplicationMaterialDAO = dao

    async def create_application_material(
        self, application_material: ApplicationMaterialCreate
    ):
        """Create a new application material."""
        return await self.dao.create_application_material(application_material)

    async def get_application_material(self, application_id: int):
        """Get application material by application ID."""
        return await self.dao.get_application_material(application_id)

    async def get_application_materials(self):
        """Get all application materials."""
        return await self.dao.get_application_materials()

    async def delete_application_material(self, application_id: int):
        """Delete application material."""
        return await self.dao.delete_application_material(application_id)


async def get_application_material_service(
    application_material_dao: ApplicationMaterialDAO = Depends(
        get_application_material_dao
    ),
) -> ApplicationMaterialService:
    """Dependency injection for ApplicationMaterialService."""
    return ApplicationMaterialService(application_material_dao)


async def get_application_service(
    application_dao: ApplicationDAO = Depends(get_application_dao),
) -> ApplicationService:
    """Dependency injection for ApplicationService."""
    return ApplicationService(application_dao)
