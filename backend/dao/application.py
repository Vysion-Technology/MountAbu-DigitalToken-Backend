"""Application DAO."""

from fastapi import HTTPException
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import insert, select

from backend.database import get_db
from backend.dbmodels.application import ApplicationComment
from backend.dao.base import BaseDAO
from backend.meta import ApplicationStatus
from backend.schemas.request.application import ApplicationCreate
from backend.schemas.response.application import ApplicationResponse
from backend.schemas.response.meta import SuccessResponse
from backend.dbmodels.application import Application


class ApplicationDAO(BaseDAO):
    """Application DAO."""

    async def create_application(
        self, application: ApplicationCreate
    ) -> ApplicationResponse:
        """Create application."""
        application = await self.session.execute(
            insert(Application).values(**application.dict()).returning(Application)
        )
        await self.session.commit()
        return ApplicationResponse.model_validate(application.scalar_one())

    async def get_application(self, application_id: int) -> ApplicationResponse:
        """Get application."""
        application = await self.session.get(Application, application_id)
        return ApplicationResponse.model_validate(application)

    async def get_applications(
        self, user_id: Optional[int] = None, offset: int = 0, limit: int = 10
    ) -> list[ApplicationResponse]:
        """Get applications."""
        query = select(Application)
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


async def get_application_dao(
    session: AsyncSession = Depends(get_db),
) -> ApplicationDAO:
    """..."""
    return ApplicationDAO(session)
