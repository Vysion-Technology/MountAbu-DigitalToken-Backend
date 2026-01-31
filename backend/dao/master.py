from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional, Type, TypeVar

from backend.database import Base
from backend.dbmodels.master import Ward, Department, Role, ComplaintCategory
from backend.schemas.request.master import (
    WardCreate, WardUpdate,
    DepartmentCreate, DepartmentUpdate,
    RoleCreate, RoleUpdate,
    ComplaintCategoryCreate, ComplaintCategoryUpdate
)

T = TypeVar("T", bound=Base)

class MasterDataDAO:
    async def _create(self, session: AsyncSession, model: Type[T], data: dict) -> T:
        db_obj = model(**data)
        session.add(db_obj)
        await session.flush()
        return db_obj

    async def _get(self, session: AsyncSession, model: Type[T], id: int) -> Optional[T]:
        result = await session.execute(select(model).where(model.id == id))
        return result.scalar_one_or_none()

    async def _update(self, session: AsyncSession, model: Type[T], id: int, data: dict) -> Optional[T]:
        stmt = update(model).where(model.id == id).values(**data).returning(model)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _delete(self, session: AsyncSession, model: Type[T], id: int) -> bool:
        result = await session.execute(delete(model).where(model.id == id))
        return result.rowcount > 0

    async def _list(self, session: AsyncSession, model: Type[T]) -> List[T]:
        result = await session.execute(select(model))
        return result.scalars().all()

    # Ward Operations
    async def create_ward(self, session: AsyncSession, ward: WardCreate) -> Ward:
        return await self._create(session, Ward, ward.model_dump())

    async def get_ward(self, session: AsyncSession, ward_id: int) -> Optional[Ward]:
        return await self._get(session, Ward, ward_id)

    async def update_ward(self, session: AsyncSession, ward_id: int, ward: WardUpdate) -> Optional[Ward]:
        return await self._update(session, Ward, ward_id, ward.model_dump(exclude_unset=True))

    async def list_wards(self, session: AsyncSession) -> List[Ward]:
        return await self._list(session, Ward)

    # Department Operations
    async def create_department(self, session: AsyncSession, dept: DepartmentCreate) -> Department:
        return await self._create(session, Department, dept.model_dump())

    async def get_department(self, session: AsyncSession, dept_id: int) -> Optional[Department]:
        return await self._get(session, Department, dept_id)
    
    async def update_department(self, session: AsyncSession, dept_id: int, dept: DepartmentUpdate) -> Optional[Department]:
        return await self._update(session, Department, dept_id, dept.model_dump(exclude_unset=True))

    async def list_departments(self, session: AsyncSession) -> List[Department]:
        return await self._list(session, Department)

    # Role Operations
    async def create_role(self, session: AsyncSession, role: RoleCreate) -> Role:
        return await self._create(session, Role, role.model_dump())

    async def get_role(self, session: AsyncSession, role_id: int) -> Optional[Role]:
        return await self._get(session, Role, role_id)
    
    async def update_role(self, session: AsyncSession, role_id: int, role: RoleUpdate) -> Optional[Role]:
        return await self._update(session, Role, role_id, role.model_dump(exclude_unset=True))

    async def list_roles(self, session: AsyncSession) -> List[Role]:
        return await self._list(session, Role)

    # Complaint Category Operations
    async def create_complaint_category(self, session: AsyncSession, category: ComplaintCategoryCreate) -> ComplaintCategory:
        return await self._create(session, ComplaintCategory, category.model_dump())
    
    async def get_complaint_category(self, session: AsyncSession, category_id: int) -> Optional[ComplaintCategory]:
        return await self._get(session, ComplaintCategory, category_id)

    async def update_complaint_category(self, session: AsyncSession, category_id: int, category: ComplaintCategoryUpdate) -> Optional[ComplaintCategory]:
        return await self._update(session, ComplaintCategory, category_id, category.model_dump(exclude_unset=True))

    async def list_complaint_categories(self, session: AsyncSession) -> List[ComplaintCategory]:
        return await self._list(session, ComplaintCategory)
