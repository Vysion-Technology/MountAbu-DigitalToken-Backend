"""Application DAO."""

from fastapi import HTTPException
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import insert, select
from sqlalchemy.orm import selectinload


from backend.database import get_db
from backend.dbmodels.application import ApplicationComment
from backend.dao.base import BaseDAO
from backend.meta import ApplicationStatus
from backend.schemas.request.application import ApplicationCreate
from backend.schemas.response.application import ApplicationResponse
from backend.schemas.response.meta import SuccessResponse
from backend.dbmodels.application import Application, ApplicationDocument
from backend.meta import ApplicationDocumentType


class ApplicationDAO(BaseDAO):
    """Application DAO."""

    async def create_application(
        self, application: ApplicationCreate, user_id: int, mobile: str
    ) -> ApplicationResponse:
        """Create application."""
        # Extract material requirements before creating application
        material_requirements = application.material_requirements
        application_data = application.model_dump(exclude={"material_requirements"})
        application_data["user_id"] = user_id
        application_data["mobile"] = mobile

        # Validate that all material IDs exist
        if material_requirements:
            from backend.dbmodels.application import Material, ApplicationMaterial

            material_ids = [m.material_id for m in material_requirements]

            # Query existing materials
            stmt = select(Material.id).where(Material.id.in_(material_ids))
            result = await self.session.execute(stmt)
            existing_ids = set(result.scalars().all())

            # Check for invalid material IDs
            invalid_ids = [mid for mid in material_ids if mid not in existing_ids]
            if invalid_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid material IDs: {invalid_ids}. These materials do not exist.",
                )

        # Create the application
        result = await self.session.execute(
            insert(Application).values(**application_data).returning(Application.id)
        )
        new_application_id = result.scalar_one()

        # Insert material requirements into ApplicationMaterial table
        if material_requirements:
            for material in material_requirements:
                await self.session.execute(
                    insert(ApplicationMaterial).values(
                        application_id=new_application_id,
                        material_id=material.material_id,
                        quantity=material.material_qty,
                    )
                )

        await self.session.commit()

        # Re-fetch the application with all relationships loaded
        stmt = (
            select(Application)
            .where(Application.id == new_application_id)
            .options(
                selectinload(Application.documents),
                selectinload(Application.materials),
            )
        )
        result = await self.session.execute(stmt)
        new_application = result.scalar_one()

        return ApplicationResponse.model_validate(new_application)

    async def get_application(self, application_id: int) -> ApplicationResponse:
        """Get application."""
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.documents),
                selectinload(Application.materials),
            )
        )
        result = await self.session.execute(stmt)
        application = result.scalar_one_or_none()

        # application = await self.session.get(Application, application_id) # Old method
        if not application:
            return None  # Handle outside

        return ApplicationResponse.model_validate(application)

    async def get_applications(
        self, user_id: Optional[int] = None, offset: int = 0, limit: int = 10
    ) -> list[ApplicationResponse]:
        """Get applications."""
        query = select(Application).options(
            selectinload(Application.documents),
            selectinload(Application.materials),
        )
        if user_id:
            query = query.where(Application.user_id == user_id)

        applications = await self.session.scalars(query.offset(offset).limit(limit))
        return [
            ApplicationResponse.model_validate(application)
            for application in applications
        ]

    async def comment_on_application(
        self, application_id: int, comment: str, user_id: int
    ) -> SuccessResponse:
        """Comment on application."""
        comment = await self.session.execute(
            insert(ApplicationComment)
            .values(application_id=application_id, comment=comment)
            .returning(ApplicationComment)
        )
        await self.session.commit()
        return SuccessResponse()

    async def approve_application(self, application_id: int) -> SuccessResponse:
        """Approve an Application."""
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        application.status = ApplicationStatus.APPROVED
        await self.session.commit()
        return SuccessResponse()

    async def delete_application(self, application_id: int) -> SuccessResponse:
        """Delete an Application."""
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        await self.session.delete(application)
        await self.session.commit()
        return SuccessResponse()

    async def add_document(
        self,
        application_id: int,
        document_path: str,
        document_type: ApplicationDocumentType,
        user_id: int,
        document_name: Optional[str] = None,
    ) -> SuccessResponse:
        """Add document record."""
        await self.session.execute(
            insert(ApplicationDocument).values(
                application_id=application_id,
                document_path=document_path,
                document_type=document_type,
                document_by=user_id,
                document_name=document_name,
            )
        )
        await self.session.commit()
        return SuccessResponse()


async def get_application_dao(
    session: AsyncSession = Depends(get_db),
) -> ApplicationDAO:
    """..."""
    return ApplicationDAO(session)
