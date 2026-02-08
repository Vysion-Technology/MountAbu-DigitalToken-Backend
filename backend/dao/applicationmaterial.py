from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dbmodels.application import (
    ApplicationPhaseMaterial as ApplicationMaterial,
)
from backend.schemas.request.application import ApplicationMaterialCreate
from backend.dao.base import BaseDAO


class ApplicationMaterialDAO(BaseDAO):
    """..."""

    async def create_application_material(
        self, application_material: ApplicationMaterialCreate
    ):
        """..."""
        am = ApplicationMaterial(**application_material.dict())
        self.session.add(am)
        await self.session.flush()
        return am

    async def get_application_material(self, application_id: int):
        """..."""
        return await self.session.execute(
            select(ApplicationMaterial).where(
                ApplicationMaterial.application_id == application_id
            )
        )

    async def get_application_materials(self):
        """..."""
        return await self.session.execute(select(ApplicationMaterial))

    async def delete_application_material(self, application_id: int):
        """..."""
        await self.session.execute(
            delete(ApplicationMaterial).where(
                ApplicationMaterial.application_id == application_id
            )
        )


async def get_application_material_dao(
    session: AsyncSession = Depends(get_db),
) -> ApplicationMaterialDAO:
    """..."""
    return ApplicationMaterialDAO(session)
