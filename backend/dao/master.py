from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, cast, Date
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

from backend.database import Base
from backend.dbmodels.master import (
    Ward,
    Department,
    Role,
    ComplaintCategory,
    SlotDefinition,
    VehicleType,
    ScheduleBlackout,
    Announcement,
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
    ScheduleBlackoutCreate,
    ScheduleBlackoutUpdate,
    AnnouncementCreate,
    AnnouncementUpdate,
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

    # Schedule Blackout Operations
    async def _cancel_schedules_for_blackout(
        self, session: AsyncSession, blackout: ScheduleBlackout
    ) -> int:
        """Auto-cancel active vehicle schedules affected by a blackout and dispatch mock cancellation SMS to citizens."""
        from backend.dbmodels.application import VehicleSchedule
        from backend.meta import VehicleScheduleStatus
        from backend.services.sms import sms_service

        target_date = (
            blackout.blackout_date.date()
            if hasattr(blackout.blackout_date, "date")
            else blackout.blackout_date
        )

        stmt = (
            select(VehicleSchedule)
            .where(
                and_(
                    cast(VehicleSchedule.schedule_date, Date) == target_date,
                    VehicleSchedule.status == VehicleScheduleStatus.SCHEDULED,
                )
            )
            .options(
                joinedload(VehicleSchedule.user),
                joinedload(VehicleSchedule.application),
            )
        )
        if not blackout.is_full_day and blackout.slot_id is not None:
            stmt = stmt.where(VehicleSchedule.slot_id == blackout.slot_id)

        res = await session.execute(stmt)
        affected_schedules = res.scalars().all()

        cancelled_count = 0
        now = datetime.now()
        for sched in affected_schedules:
            sched.status = VehicleScheduleStatus.CANCELLED
            sched.cancelled_at = now
            cancelled_count += 1

            # Dispatch notification / mock SMS to citizen
            citizen_mobile = None
            if sched.user and hasattr(sched.user, "mobile") and sched.user.mobile:
                citizen_mobile = sched.user.mobile
            elif sched.application and hasattr(sched.application, "mobile") and sched.application.mobile:
                citizen_mobile = sched.application.mobile

            if citizen_mobile:
                try:
                    await sms_service.send_schedule_cancellation_sms(
                        mobile=citizen_mobile,
                        vehicle_number=sched.vehicle_number,
                        schedule_date=str(target_date),
                        reason=blackout.reason,
                    )
                except Exception as ex:
                    logger.error(
                        f"Failed to send cancellation SMS for schedule {sched.id}: {ex}"
                    )

        if cancelled_count > 0:
            await session.commit()
            logger.info(
                f"Auto-cancelled {cancelled_count} vehicle schedule(s) for blackout on {target_date} ({blackout.reason})"
            )

        return cancelled_count

    async def create_blackout(
        self,
        session: AsyncSession,
        blackout: ScheduleBlackoutCreate,
        created_by_id: Optional[int] = None,
    ) -> ScheduleBlackout:
        data = blackout.model_dump()
        if created_by_id:
            data["created_by_id"] = created_by_id
        db_obj = ScheduleBlackout(**data)
        session.add(db_obj)
        await session.commit()

        if db_obj.is_active:
            await self._cancel_schedules_for_blackout(session, db_obj)

        return await self.get_blackout(session, db_obj.id, active_only=False)

    async def get_blackout(
        self, session: AsyncSession, blackout_id: int, active_only: bool = False
    ) -> Optional[ScheduleBlackout]:
        stmt = (
            select(ScheduleBlackout)
            .where(ScheduleBlackout.id == blackout_id)
            .options(
                joinedload(ScheduleBlackout.slot),
                joinedload(ScheduleBlackout.created_by),
            )
        )
        if active_only:
            stmt = stmt.where(ScheduleBlackout.is_active == True)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_blackouts(
        self, session: AsyncSession, active_only: bool = False
    ) -> List[ScheduleBlackout]:
        stmt = (
            select(ScheduleBlackout)
            .options(
                joinedload(ScheduleBlackout.slot),
                joinedload(ScheduleBlackout.created_by),
            )
        )
        if active_only:
            stmt = stmt.where(ScheduleBlackout.is_active == True)
        stmt = stmt.order_by(ScheduleBlackout.blackout_date.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_blackout(
        self, session: AsyncSession, blackout_id: int, blackout: ScheduleBlackoutUpdate
    ) -> Optional[ScheduleBlackout]:
        stmt = (
            update(ScheduleBlackout)
            .where(ScheduleBlackout.id == blackout_id)
            .values(**blackout.model_dump(exclude_unset=True))
            .returning(ScheduleBlackout.id)
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        if not row:
            return None
        updated_blackout = await self.get_blackout(session, row[0], active_only=False)
        if updated_blackout and updated_blackout.is_active:
            await self._cancel_schedules_for_blackout(session, updated_blackout)
        return updated_blackout

    async def delete_blackout(self, session: AsyncSession, blackout_id: int) -> bool:
        return await self._delete(session, ScheduleBlackout, blackout_id)

    # ── Announcements ────────────────────────────────────────────────────────
    async def create_announcement(
        self,
        session: AsyncSession,
        announcement: AnnouncementCreate,
        created_by_id: Optional[int] = None,
    ) -> Announcement:
        data = announcement.model_dump()
        if created_by_id:
            data["created_by_id"] = created_by_id
        db_obj = Announcement(**data)
        session.add(db_obj)
        await session.commit()
        return await self.get_announcement(session, db_obj.id, active_only=False)

    async def get_announcement(
        self, session: AsyncSession, announcement_id: int, active_only: bool = False
    ) -> Optional[Announcement]:
        stmt = (
            select(Announcement)
            .where(Announcement.id == announcement_id)
            .options(joinedload(Announcement.created_by))
        )
        if active_only:
            stmt = stmt.where(Announcement.is_active == True)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_announcements(
        self, session: AsyncSession, active_only: bool = False
    ) -> List[Announcement]:
        stmt = (
            select(Announcement)
            .options(joinedload(Announcement.created_by))
        )
        if active_only:
            stmt = stmt.where(Announcement.is_active == True)
        stmt = stmt.order_by(Announcement.id.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_announcement(
        self, session: AsyncSession, announcement_id: int, announcement: AnnouncementUpdate
    ) -> Optional[Announcement]:
        stmt = (
            update(Announcement)
            .where(Announcement.id == announcement_id)
            .values(**announcement.model_dump(exclude_unset=True))
            .returning(Announcement.id)
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        if not row:
            return None
        return await self.get_announcement(session, row[0], active_only=False)

    async def delete_announcement(self, session: AsyncSession, announcement_id: int) -> bool:
        return await self._delete(session, Announcement, announcement_id)





