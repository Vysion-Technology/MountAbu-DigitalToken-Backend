import secrets
from datetime import date, datetime, time
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.orm import selectinload

from backend.dbmodels.application import (
    VehicleSchedule,
    ApprovedApplicationPhase,
    Application,
    VehicleEntry,
)
from backend.dbmodels.master import SlotDefinition, VehicleType
from backend.meta import VehicleScheduleStatus, ApplicationPhaseStatus
from backend.schemas.request.schedule import VehicleScheduleCreate
from backend.schemas.response.schedule import (
    AvailableSlotItemResponse,
    AvailableSlotsResponse,
    VehicleScheduleResponse,
)


class VehicleScheduleDAO:
    async def get_active_schedule_by_token(
        self, session: AsyncSession, token_id: int
    ) -> Optional[VehicleSchedule]:
        """Check if an active (SCHEDULED) booking exists for this token."""
        stmt = (
            select(VehicleSchedule)
            .where(
                and_(
                    VehicleSchedule.token_id == token_id,
                    VehicleSchedule.status == VehicleScheduleStatus.SCHEDULED,
                )
            )
            .options(
                selectinload(VehicleSchedule.slot),
                selectinload(VehicleSchedule.vehicle_type),
                selectinload(VehicleSchedule.application),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_schedule_for_token_on_date(
        self, session: AsyncSession, token_id: int, target_date: date
    ) -> Optional[VehicleSchedule]:
        """Fetch scheduled booking for this token on a specific date."""
        stmt = (
            select(VehicleSchedule)
            .where(
                and_(
                    VehicleSchedule.token_id == token_id,
                    cast(VehicleSchedule.schedule_date, Date) == target_date,
                    VehicleSchedule.status == VehicleScheduleStatus.SCHEDULED,
                )
            )
            .options(
                selectinload(VehicleSchedule.slot),
                selectinload(VehicleSchedule.vehicle_type),
                selectinload(VehicleSchedule.application),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_slot_booked_count(
        self, session: AsyncSession, slot_id: int, target_date: date
    ) -> int:
        """Count active scheduled bookings for a given slot and date."""
        stmt = select(func.count(VehicleSchedule.id)).where(
            and_(
                VehicleSchedule.slot_id == slot_id,
                cast(VehicleSchedule.schedule_date, Date) == target_date,
                VehicleSchedule.status == VehicleScheduleStatus.SCHEDULED,
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def get_available_slots_for_date(
        self, session: AsyncSession, target_date: date
    ) -> AvailableSlotsResponse:
        """Get all active slots and their booked/available capacities for the specified date."""
        # 1. Fetch all active slots ordered by start_time
        slot_stmt = (
            select(SlotDefinition)
            .where(SlotDefinition.is_active == True)
            .order_by(SlotDefinition.start_time.asc())
        )
        slot_res = await session.execute(slot_stmt)
        slots = slot_res.scalars().all()

        slot_items: List[AvailableSlotItemResponse] = []
        for s in slots:
            booked_count = await self.get_slot_booked_count(session, s.id, target_date)
            avail = max(0, s.max_capacity - booked_count)
            slot_items.append(
                AvailableSlotItemResponse(
                    slot_id=s.id,
                    name=s.name,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    max_capacity=s.max_capacity,
                    booked_count=booked_count,
                    available_capacity=avail,
                    is_available=avail > 0,
                )
            )

        return AvailableSlotsResponse(date=target_date, slots=slot_items)

    async def create_schedule(
        self,
        session: AsyncSession,
        user_id: int,
        schedule_in: VehicleScheduleCreate,
    ) -> VehicleSchedule:
        """Create a vehicle schedule booking with strict validations."""
        # 1. Verify token exists and is active
        token_stmt = select(ApprovedApplicationPhase).where(
            ApprovedApplicationPhase.id == schedule_in.token_id
        )
        token_res = await session.execute(token_stmt)
        token = token_res.scalar_one_or_none()
        if not token:
            raise ValueError(f"Token with ID {schedule_in.token_id} not found.")
        if token.status != ApplicationPhaseStatus.ACTIVE:
            raise ValueError(f"Token is not active (current status: {token.status.value}). Only active tokens can schedule vehicle entries.")

        # 2. Strict Check: Ensure token does not already have an active schedule
        existing_active = await self.get_active_schedule_by_token(session, schedule_in.token_id)
        if existing_active:
            raise ValueError(
                f"An active vehicle schedule ({existing_active.schedule_code}) already exists for this token for date {existing_active.schedule_date.strftime('%Y-%m-%d')}. "
                f"Please complete or cancel the existing schedule before booking a new one."
            )

        # 3. Verify slot definition exists and is active
        slot_stmt = select(SlotDefinition).where(
            and_(SlotDefinition.id == schedule_in.slot_id, SlotDefinition.is_active == True)
        )
        slot_res = await session.execute(slot_stmt)
        slot = slot_res.scalar_one_or_none()
        if not slot:
            raise ValueError("Selected time slot is invalid or inactive.")

        # 4. Verify capacity for selected slot on target date
        booked_count = await self.get_slot_booked_count(session, slot.id, schedule_in.schedule_date)
        if booked_count >= slot.max_capacity:
            raise ValueError(f"Selected time slot '{slot.name}' on {schedule_in.schedule_date} is fully booked ({booked_count}/{slot.max_capacity}). Please choose another slot.")

        # 5. Format schedule code
        date_str = schedule_in.schedule_date.strftime("%Y%m%d")
        rand_suffix = secrets.token_hex(2).upper()
        schedule_code = f"SCH-{date_str}-{rand_suffix}"

        # 6. Construct DateTime from date
        schedule_dt = datetime.combine(schedule_in.schedule_date, time(0, 0))

        # 7. Create schedule object
        clean_vehicle_number = schedule_in.vehicle_number.strip().upper()
        db_schedule = VehicleSchedule(
            schedule_code=schedule_code,
            application_id=token.application_id,
            phase=token.phase,
            user_id=user_id,
            slot_id=slot.id,
            schedule_date=schedule_dt,
            vehicle_number=clean_vehicle_number,
            vehicle_type_id=schedule_in.vehicle_type_id,
            status=VehicleScheduleStatus.SCHEDULED,
            created_at=datetime.now(),
        )

        session.add(db_schedule)
        await session.commit()
        await session.refresh(db_schedule)

        return await self.get_schedule_by_id(session, db_schedule.id)

    async def get_schedule_by_id(
        self, session: AsyncSession, schedule_id: int
    ) -> Optional[VehicleSchedule]:
        """Fetch schedule by primary key with relations."""
        stmt = (
            select(VehicleSchedule)
            .where(VehicleSchedule.id == schedule_id)
            .options(
                selectinload(VehicleSchedule.slot),
                selectinload(VehicleSchedule.vehicle_type),
                selectinload(VehicleSchedule.application),
                selectinload(VehicleSchedule.user),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_schedules_by_user(
        self, session: AsyncSession, user_id: int
    ) -> List[VehicleSchedule]:
        """Fetch all schedules created by a citizen."""
        stmt = (
            select(VehicleSchedule)
            .where(VehicleSchedule.user_id == user_id)
            .options(
                selectinload(VehicleSchedule.slot),
                selectinload(VehicleSchedule.vehicle_type),
                selectinload(VehicleSchedule.application),
            )
            .order_by(VehicleSchedule.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def cancel_schedule(
        self, session: AsyncSession, schedule_id: int, user_id: Optional[int] = None
    ) -> VehicleSchedule:
        """Cancel a pending schedule."""
        schedule = await self.get_schedule_by_id(session, schedule_id)
        if not schedule:
            raise ValueError(f"Schedule with ID {schedule_id} not found.")

        if user_id and schedule.user_id != user_id:
            raise ValueError("You do not have permission to cancel this schedule.")

        if schedule.status != VehicleScheduleStatus.SCHEDULED:
            raise ValueError(f"Cannot cancel schedule in '{schedule.status.value}' status.")

        schedule.status = VehicleScheduleStatus.CANCELLED
        schedule.cancelled_at = datetime.now()
        await session.commit()
        await session.refresh(schedule)
        return schedule

    async def complete_schedule(
        self, session: AsyncSession, schedule_id: int
    ) -> Optional[VehicleSchedule]:
        """Mark schedule as completed when vehicle entry is made."""
        schedule = await self.get_schedule_by_id(session, schedule_id)
        if schedule and schedule.status == VehicleScheduleStatus.SCHEDULED:
            schedule.status = VehicleScheduleStatus.COMPLETED
            await session.commit()
            await session.refresh(schedule)
        return schedule
