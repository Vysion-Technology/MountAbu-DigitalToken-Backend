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
        return await self.session.add(am)


async def get_application_material_dao():
    """..."""
    return ApplicationMaterialDAO()
