from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Optional, Type, TypeVar

from backend.database import Base
from backend.dbmodels.master import (
    Ward,
    Department,
    Role,
    ComplaintCategory,
    SlotDefinition,
    VehicleType,
)
from backend.dbmodels.application import Material
from backend.schemas.request.master import (
    WardCreate,
    WardUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    RoleCreate,
    RoleUpdate,
    ComplaintCategoryCreate,
    ComplaintCategoryUpdate,
    MaterialCreate,
    MaterialUpdate,
    SlotDefinitionCreate,
    SlotDefinitionUpdate,
    VehicleTypeCreate,
    VehicleTypeUpdate,
)

T = TypeVar("T", bound=Base)


class MasterDataDAO:
    async def _create(self, session: AsyncSession, model: Type[T], data: dict) -> T:
        db_obj = model(**data)
        session.add(db_obj)
        await session.commit()
        # Refresh and load relationships
        stmt = select(model).where(model.id == db_obj.id)
        if hasattr(model, "created_by"):
            stmt = stmt.options(joinedload(getattr(model, "created_by")))
        result = await session.execute(stmt)
        return result.scalar_one()

    async def _get(self, session: AsyncSession, model: Type[T], id: int, active_only: bool = False) -> Optional[T]:
        stmt = select(model).where(model.id == id)
        if active_only:
            if hasattr(model, "status"):
                stmt = stmt.where(getattr(model, "status") == True)
            elif hasattr(model, "is_active"):
                stmt = stmt.where(getattr(model, "is_active") == True)
        if hasattr(model, "created_by"):
            stmt = stmt.options(joinedload(getattr(model, "created_by")))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _update(
        self, session: AsyncSession, model: Type[T], id: int, data: dict
    ) -> Optional[T]:
        stmt = update(model).where(model.id == id).values(**data).returning(model.id)
        result = await session.execute(stmt)
        row = result.fetchone()
        if not row:
            return None
        return await self._get(session, model, row[0], active_only=False)

    async def _delete(self, session: AsyncSession, model: Type[T], id: int) -> bool:
        result = await session.execute(delete(model).where(model.id == id))
        return result.rowcount > 0

    async def _list(self, session: AsyncSession, model: Type[T], active_only: bool = False) -> List[T]:
        stmt = select(model)
        if active_only:
            if hasattr(model, "status"):
                stmt = stmt.where(getattr(model, "status") == True)
            elif hasattr(model, "is_active"):
                stmt = stmt.where(getattr(model, "is_active") == True)
        if hasattr(model, "created_by"):
            stmt = stmt.options(joinedload(getattr(model, "created_by")))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # Ward Operations
    async def create_ward(
        self,
        session: AsyncSession,
        ward: WardCreate,
        created_by_id: Optional[int] = None,
    ) -> Ward:
        data = ward.model_dump()
        if created_by_id:
            data["created_by_id"] = created_by_id
        return await self._create(session, Ward, data)

    async def get_ward(self, session: AsyncSession, ward_id: int, active_only: bool = False) -> Optional[Ward]:
        return await self._get(session, Ward, ward_id, active_only=active_only)

    async def update_ward(
        self, session: AsyncSession, ward_id: int, ward: WardUpdate
    ) -> Optional[Ward]:
        return await self._update(
            session, Ward, ward_id, ward.model_dump(exclude_unset=True)
        )

    async def list_wards(self, session: AsyncSession, active_only: bool = False) -> List[Ward]:
        return await self._list(session, Ward, active_only=active_only)

    async def delete_ward(self, session: AsyncSession, ward_id: int) -> bool:
        return await self._delete(session, Ward, ward_id)

    # Department Operations
    async def create_department(
        self,
        session: AsyncSession,
        dept: DepartmentCreate,
        created_by_id: Optional[int] = None,
    ) -> Department:
        data = dept.model_dump()
        if created_by_id:
            data["created_by_id"] = created_by_id
        
        # Create
        obj = Department(**data)
        session.add(obj)
        await session.flush()
        
        # Re-fetch with relationships
        stmt = (
            select(Department)
            .where(Department.id == obj.id)
            .options(selectinload(Department.jen), selectinload(Department.created_by))
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def get_department(
        self, session: AsyncSession, dept_id: int, active_only: bool = False
    ) -> Optional[Department]:
        stmt = (
            select(Department)
            .where(Department.id == dept_id)
            .options(selectinload(Department.jen), selectinload(Department.created_by))
        )
        if active_only:
            stmt = stmt.where(Department.status == True)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_department(
        self, session: AsyncSession, dept_id: int, dept: DepartmentUpdate
    ) -> Optional[Department]:
        data = dept.model_dump(exclude_unset=True)
        if data:
            stmt = update(Department).where(Department.id == dept_id).values(**data)
            await session.execute(stmt)
            await session.flush()
            
        return await self.get_department(session, dept_id, active_only=False)

    async def list_departments(self, session: AsyncSession, active_only: bool = False) -> List[Department]:
        stmt = (
            select(Department)
            .options(selectinload(Department.jen), selectinload(Department.created_by))
            .order_by(Department.id)
        )
        if active_only:
            stmt = stmt.where(Department.status == True)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete_department(self, session: AsyncSession, dept_id: int) -> bool:
        return await self._delete(session, Department, dept_id)

    # Role Operations
    async def create_role(
        self,
        session: AsyncSession,
        role: RoleCreate,
        created_by_id: Optional[int] = None,
    ) -> Role:
        data = role.model_dump()
        if created_by_id:
            data["created_by_id"] = created_by_id
        return await self._create(session, Role, data)

    async def get_role(self, session: AsyncSession, role_id: int, active_only: bool = False) -> Optional[Role]:
        return await self._get(session, Role, role_id, active_only=active_only)

    async def update_role(
        self, session: AsyncSession, role_id: int, role: RoleUpdate
    ) -> Optional[Role]:
        return await self._update(
            session, Role, role_id, role.model_dump(exclude_unset=True)
        )

    async def list_roles(self, session: AsyncSession, active_only: bool = False) -> List[Role]:
        return await self._list(session, Role, active_only=active_only)

    async def delete_role(self, session: AsyncSession, role_id: int) -> bool:
        return await self._delete(session, Role, role_id)

    # Complaint Category Operations
    async def create_complaint_category(
        self,
        session: AsyncSession,
        category: ComplaintCategoryCreate,
        created_by_id: Optional[int] = None,
    ) -> ComplaintCategory:
        data = category.model_dump()
        if created_by_id:
            data["created_by_id"] = created_by_id
        return await self._create(session, ComplaintCategory, data)

    async def get_complaint_category(
        self, session: AsyncSession, category_id: int, active_only: bool = False
    ) -> Optional[ComplaintCategory]:
        return await self._get(session, ComplaintCategory, category_id, active_only=active_only)

    async def update_complaint_category(
        self, session: AsyncSession, category_id: int, category: ComplaintCategoryUpdate
    ) -> Optional[ComplaintCategory]:
        return await self._update(
            session,
            ComplaintCategory,
            category_id,
            category.model_dump(exclude_unset=True),
        )

    async def list_complaint_categories(
        self, session: AsyncSession, active_only: bool = False
    ) -> List[ComplaintCategory]:
        return await self._list(session, ComplaintCategory, active_only=active_only)

    async def delete_complaint_category(
        self, session: AsyncSession, category_id: int
    ) -> bool:
        return await self._delete(session, ComplaintCategory, category_id)

    # Material Operations
    async def create_material(
        self,
        session: AsyncSession,
        material: MaterialCreate,
        created_by_id: Optional[int] = None,
    ) -> Material:
        # Import here to avoid circular dependencies if any, or just standard import at top
        from backend.dbmodels.application import Material

        data = material.model_dump()
        if created_by_id:
            data["created_by_id"] = created_by_id
        return await self._create(session, Material, data)

    async def list_materials(self, session: AsyncSession, active_only: bool = False) -> List[Material]:
        from backend.dbmodels.application import Material

        return await self._list(session, Material, active_only=active_only)

    async def update_material(
        self, session: AsyncSession, material_id: int, material: MaterialUpdate
    ) -> Optional[Material]:
        from backend.dbmodels.application import Material

        return await self._update(
            session, Material, material_id, material.model_dump(exclude_unset=True)
        )

    async def delete_material(self, session: AsyncSession, material_id: int) -> bool:
        from backend.dbmodels.application import Material

        return await self._delete(session, Material, material_id)

    # Slot Definition Operations
    async def create_slot(
        self,
        session: AsyncSession,
        slot: SlotDefinitionCreate,
        created_by_id: Optional[int] = None,
    ) -> SlotDefinition:
        data = slot.model_dump()
        if created_by_id:
            data["created_by_id"] = created_by_id
        return await self._create(session, SlotDefinition, data)

    async def get_slot(
        self, session: AsyncSession, slot_id: int, active_only: bool = False
    ) -> Optional[SlotDefinition]:
        return await self._get(session, SlotDefinition, slot_id, active_only=active_only)

    async def list_slots(
        self, session: AsyncSession, active_only: bool = False
    ) -> List[SlotDefinition]:
        return await self._list(session, SlotDefinition, active_only=active_only)

    async def update_slot(
        self, session: AsyncSession, slot_id: int, slot: SlotDefinitionUpdate
    ) -> Optional[SlotDefinition]:
        return await self._update(
            session, SlotDefinition, slot_id, slot.model_dump(exclude_unset=True)
        )

    async def delete_slot(self, session: AsyncSession, slot_id: int) -> bool:
        return await self._delete(session, SlotDefinition, slot_id)

    # Vehicle Type Operations
    async def create_vehicle_type(
        self,
        session: AsyncSession,
        vehicle_type: VehicleTypeCreate,
        created_by_id: Optional[int] = None,
    ) -> VehicleType:
        data = vehicle_type.model_dump()
        if created_by_id:
            data["created_by_id"] = created_by_id
        return await self._create(session, VehicleType, data)

    async def get_vehicle_type(
        self, session: AsyncSession, vehicle_type_id: int, active_only: bool = False
    ) -> Optional[VehicleType]:
        return await self._get(session, VehicleType, vehicle_type_id, active_only=active_only)

    async def list_vehicle_types(
        self, session: AsyncSession, active_only: bool = False
    ) -> List[VehicleType]:
        return await self._list(session, VehicleType, active_only=active_only)

    async def update_vehicle_type(
        self, session: AsyncSession, vehicle_type_id: int, vehicle_type: VehicleTypeUpdate
    ) -> Optional[VehicleType]:
        return await self._update(
            session, VehicleType, vehicle_type_id, vehicle_type.model_dump(exclude_unset=True)
        )

    async def delete_vehicle_type(self, session: AsyncSession, vehicle_type_id: int) -> bool:
        return await self._delete(session, VehicleType, vehicle_type_id)

