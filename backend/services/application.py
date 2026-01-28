from backend.dao.applicationmaterial import ApplicationMaterialDAO
from backend.dao.applicationmaterial import get_application_material_dao
from backend.schemas.request.application import ApplicationMaterialCreate
from fastapi import Depends, UploadFile

from backend.schemas.base.auth import UserDetails
from backend.dao.application import get_application_dao
from backend.dao.application import ApplicationDAO
from backend.services.base import BaseService
from backend.schemas.request.application import ApplicationCreate
from backend.services.storage import get_storage_service
from backend.meta import ApplicationDocumentType


class ApplicationService(BaseService):
    """..."""

    def __init__(self, dao: ApplicationDAO):
        self.dao = dao

    async def create_application(self, application: ApplicationCreate):
        """..."""
        return await self.dao.create_application(application)

    async def get_application(self, application_id: int, user: UserDetails):
        """..."""
        return await self.dao.get_application(application_id)

    async def get_applications(self, user_id: int, offset: int, limit: int):
        """..."""
        return await self.dao.get_applications(user_id, offset, limit)

    async def delete_application(self, application_id: int):
        """..."""
        return await self.dao.delete_application(application_id)

    async def upload_document(
        self, application_id: int, document: UploadFile, user_id: int
    ):
        """Upload and save document."""
        storage = get_storage_service()
        if not storage:
            # Handle error appropriately
            raise Exception("Storage service unavailable")

        file_path = f"applications/{application_id}/{document.filename}"
        path = await storage.upload_file(document, file_path)

        await self.dao.add_document(
            application_id=application_id,
            document_path=path,
            document_type=ApplicationDocumentType.OTHERS,  # Default
            user_id=user_id,
            document_name=document.filename,
        )
        return {"message": "Document uploaded successfully", "path": path}

    async def delete_document(self, application_id: int, document_id: int):
        """Delete a document from an application."""

    async def update_application(
        self, application_id: int, application: ApplicationCreate
    ):
        """..."""
        return await self.dao.update_application(application_id, application)


class ApplicationMaterialService(BaseService):
    """..."""

    def __init__(self, dao: ApplicationMaterialDAO):
        self.dao = dao

    async def create_application_material(
        self, application_material: ApplicationMaterialCreate
    ):
        """..."""
        return await self.dao.create_application_material(application_material)

    async def get_application_material(self, application_id: int):
        """..."""
        return await self.dao.get_application_material(application_id)

    async def get_application_materials(self):
        """..."""
        return await self.dao.get_application_materials()

    async def delete_application_material(self, application_id: int):
        """..."""
        return await self.dao.delete_application_material(application_id)


async def get_application_material_service(
    application_material_dao: ApplicationMaterialDAO = Depends(
        get_application_material_dao
    ),
):
    """..."""
    return ApplicationMaterialService(application_material_dao)


async def get_application_service(
    application_dao: ApplicationDAO = Depends(get_application_dao),
):
    """..."""
    return ApplicationService(application_dao)
