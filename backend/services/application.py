from datetime import datetime
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
    ApplicationPhaseStatus,
    PropertyUsageType,
)
from backend.schemas.base.auth import UserDetails
from backend.schemas.request.application import (
    ApplicationCreate,
    ApplicationMaterialCreate,
    ApplicationMaterialRequirements,
    InspectionReportCreate,
    NakaEntryCreate,
    WorkflowActionRequest,
    PhaseStatusUpdateRequest,
)
from backend.schemas.response.application import (
    ApplicationResponse,
    PhaseResponse,
    TokenResponse,
    TokenDetailResponse,
    AuthorityVehicleEntryResponse,
    NakaEntryResponse,
    VehicleEntryDetailResponse,
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
        search: Optional[str] = None,
        ward_id: Optional[int] = None,
        property_usage: Optional[PropertyUsageType] = None,
    ) -> List[ApplicationResponse]:
        """Get applications filtered by flag, search, and other criteria."""
        return await self.dao.get_applications(
            flag=flag,
            offset=offset,
            limit=limit,
            user_id=user_id,
            search=search,
            ward_id=ward_id,
            property_usage=property_usage,
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

    async def withdraw_application(
        self, application_id: int, user_id: int
    ) -> SuccessResponse:
        """Withdraw an application by the applicant."""
        return await self.dao.withdraw_application(application_id, user_id)

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

    async def update_phase_materials(
        self, application_id: int, phase_materials: list
    ) -> SuccessResponse:
        """Update phase-wise materials for an application (used by JEN)."""
        return await self.dao.update_phase_materials(application_id, phase_materials)

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
        media = {
            "vehicle_plate": entry.vehicle_plate_image,
            "entry_proofs": entry.entry_proof_images,
        }
        return await self.dao.create_naka_entry(
            application_id=application_id,
            phase=phase,
            user_id=user_id,
            materials=[m.model_dump() for m in entry.materials],
            vehicle_number=entry.vehicle_number,
            vehicle_type=entry.vehicle_type,
            latitude=entry.latitude,
            longitude=entry.longitude,
            remarks=entry.remarks,
            media=media,
        )

    async def upload_dumping_photo(
        self, application_id: int, entry_id: int, document: UploadFile, user_id: int
    ) -> DocumentUploadResponse:
        """Upload and save dumping photo for a vehicle entry."""
        storage = get_storage_service()
        if not storage:
            raise Exception("Storage service unavailable")

        file_path = f"applications/{application_id}/vehicle-entries/{entry_id}/dumping-photos/{document.filename}"
        path = await storage.upload_file(document, file_path)

        await self.dao.add_dumping_photo(
            application_id=application_id,
            entry_id=entry_id,
            photo_path=path,
            user_id=user_id,
        )
        return DocumentUploadResponse(
            message="Dumping photo uploaded successfully", path=path
        )

    async def get_naka_entries(self, application_id: int) -> list:
        """Get all naka entries for an application."""

        entries = await self.dao.get_naka_entries(application_id)
        return [NakaEntryResponse.model_validate(e) for e in entries]

    async def get_vehicle_entry_detail(
        self, entry_id: int, user: UserDetails
    ) -> VehicleEntryDetailResponse:
        """Get full details for a single vehicle entry with auth check."""
        entry_data = await self.dao.get_vehicle_entry_detail(entry_id)

        # Authorization Check
        allowed_authority_roles = [
            UserRole.SUPERADMIN,
            UserRole.NODAL_OFFICER,
            UserRole.NAKA_INCHARGE,
        ]

        if user.role not in allowed_authority_roles:
            # Must be CITIZEN and own the application
            if (
                user.role != UserRole.CITIZEN
                or entry_data["application_user_id"] != user.user_id
            ):
                raise HTTPException(
                    status_code=403,
                    detail="You are not permitted to view this vehicle entry.",
                )

        return VehicleEntryDetailResponse.model_validate(entry_data)

    async def get_all_vehicle_entries(
        self,
        user_role: UserRole,
        search: Optional[str] = None,
        vehicle_number: Optional[str] = None,
        material_name: Optional[str] = None,
        token_number: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AuthorityVehicleEntryResponse]:
        """Get all vehicle entries for authority view, with role-based token_number hiding."""
        entries_data = await self.dao.get_all_vehicle_entries(
            search=search,
            vehicle_number=vehicle_number,
            material_name=material_name,
            token_number=token_number,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )

        response = []
        for item in entries_data:
            if user_role == UserRole.NAKA_INCHARGE:
                item["token_number"] = None

            response.append(AuthorityVehicleEntryResponse.model_validate(item))

        return response
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

    async def update_phase_status(
        self,
        application_id: int,
        phase: int,
        request: PhaseStatusUpdateRequest,
        user_id: int,
    ) -> SuccessResponse:
        """Manually update a phase's status."""
        return await self.dao.update_phase_status(
            application_id, phase, request.status, user_id
        )

    # ── Token queries ─────────────────────────────────────────────────────
    async def get_tokens(
        self,
        user_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 10,
    ) -> list[TokenResponse]:
        """Get all tokens with optional filters."""
        token_dicts = await self.dao.get_tokens(
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
