from typing import List, Optional

from fastapi import Depends, UploadFile

from backend.dao.application import get_application_dao, ApplicationDAO
from backend.dao.applicationmaterial import (
    ApplicationMaterialDAO,
    get_application_material_dao,
)
from backend.meta import ApplicationDocumentType, UserRole
from backend.schemas.base.auth import UserDetails
from backend.schemas.request.application import (
    ApplicationCreate,
    ApplicationMaterialCreate,
)
from backend.schemas.response.application import ApplicationResponse
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
            # TODO: Log the user access to user data here
            print(
                f"User {user.id} requested full user data for application {application_id}"
            )

        application = await self.dao.get_application(application_id)

        if application and user.role == UserRole.NAKA_INCHARGE:
            # Sanitize user details for NAKA_INCHARGE
            application.mobile = "******"
            application.email = "******"
            application.current_address = "******"

        return application

    async def get_applications(
        self, user_id: int, offset: int, limit: int
    ) -> List[ApplicationResponse]:
        """Get applications for a user with pagination."""
        return await self.dao.get_applications(user_id, offset, limit)

    async def delete_application(self, application_id: int) -> SuccessResponse:
        """Delete an application by ID."""
        return await self.dao.delete_application(application_id)

    async def upload_document(
        self, application_id: int, document: UploadFile, user_id: int
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
            document_type=ApplicationDocumentType.OTHERS,
            user_id=user_id,
            document_name=document.filename,
        )
        return DocumentUploadResponse(
            message="Document uploaded successfully", path=path
        )

    async def delete_document(
        self, application_id: int, document_id: int = None
    ) -> SuccessResponse:
        """Delete a document from an application."""
        # TODO: Implement document deletion logic
        return SuccessResponse()

    async def update_application(
        self, application_id: int, application: ApplicationCreate
    ) -> ApplicationResponse:
        """Update an application."""
        return await self.dao.update_application(application_id, application)


class ApplicationMaterialService(BaseService):
    """Service for handling application material operations."""

    def __init__(self, dao: ApplicationMaterialDAO):
        self.dao = dao

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
