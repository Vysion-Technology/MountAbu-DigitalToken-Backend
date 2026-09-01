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
from backend.dbmodels.master import SlotDefinition, VehicleType, ScheduleBlackout
from backend.meta import VehicleScheduleStatus, ApplicationPhaseStatus, ScheduleComplianceStatus
from backend.schemas.request.schedule import VehicleScheduleCreate
from backend.schemas.response.schedule import (
    AvailableSlotItemResponse,
    AvailableSlotsResponse,
    VehicleScheduleResponse,
    CapacityHeatmapResponse,
    CapacityHeatmapDay,
    CapacityHeatmapSlot,
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
        """Get all active slots and their booked/available capacities for the specified date, factoring blackouts and applicable days."""
        # 1. Check for active blackouts on this date
        blackout_stmt = select(ScheduleBlackout).where(
            and_(
                cast(ScheduleBlackout.blackout_date, Date) == target_date,
                ScheduleBlackout.is_active == True,
            )
        )
        blackout_res = await session.execute(blackout_stmt)
        blackouts = blackout_res.scalars().all()

        full_day_blackout = next((b for b in blackouts if b.is_full_day or b.slot_id is None), None)
        slot_blackout_map = {b.slot_id: b.reason for b in blackouts if b.slot_id is not None}

        # 2. Day of week check (e.g. MON, TUE, etc.)
        day_abbr = target_date.strftime("%a").upper()  # 'MON', 'TUE', etc.

        # 3. Fetch all active slots ordered by start_time
        slot_stmt = (
            select(SlotDefinition)
            .where(SlotDefinition.is_active == True)
            .order_by(SlotDefinition.start_time.asc())
        )
        slot_res = await session.execute(slot_stmt)
        slots = slot_res.scalars().all()

        slot_items: List[AvailableSlotItemResponse] = []
        for s in slots:
            # Check applicable days
            app_days = [d.strip().upper() for d in (s.applicable_days or "MON,TUE,WED,THU,FRI,SAT,SUN").split(",") if d.strip()]
            is_applicable_today = day_abbr in app_days

            # Check blackout
            is_slot_blackout = bool(full_day_blackout) or (s.id in slot_blackout_map)
            slot_blackout_reason = full_day_blackout.reason if full_day_blackout else slot_blackout_map.get(s.id)

            booked_count = await self.get_slot_booked_count(session, s.id, target_date)
            avail = max(0, s.max_capacity - booked_count)
            is_avail = avail > 0 and not is_slot_blackout and is_applicable_today

            slot_items.append(
                AvailableSlotItemResponse(
                    slot_id=s.id,
                    name=s.name,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    max_capacity=s.max_capacity,
                    booked_count=booked_count,
                    available_capacity=0 if is_slot_blackout else avail,
                    is_available=is_avail,
                    is_blackout=is_slot_blackout,
                    blackout_reason=slot_blackout_reason,
                    is_applicable_today=is_applicable_today,
                )
            )

        return AvailableSlotsResponse(
            date=target_date,
            is_full_day_blackout=bool(full_day_blackout),
            blackout_reason=full_day_blackout.reason if full_day_blackout else None,
            slots=slot_items,
        )

    async def get_capacity_heatmap(
        self, session: AsyncSession, start_date: date, days: int = 14
    ) -> CapacityHeatmapResponse:
        """Return a live capacity heatmap & load analytics across the next N days."""
        from datetime import timedelta
        end_date = start_date + timedelta(days=days - 1)

        days_list: List[CapacityHeatmapDay] = []
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            available_slots = await self.get_available_slots_for_date(session, current_date)

            total_cap = sum(s.max_capacity for s in available_slots.slots)
            total_bk = sum(s.booked_count for s in available_slots.slots)
            total_av = sum(s.available_capacity for s in available_slots.slots)
            load_pct = round((total_bk / total_cap * 100), 1) if total_cap > 0 else 0.0

            slot_heatmap: List[CapacityHeatmapSlot] = []
            for s in available_slots.slots:
                slot_load = round((s.booked_count / s.max_capacity * 100), 1) if s.max_capacity > 0 else 0.0
                slot_heatmap.append(
                    CapacityHeatmapSlot(
                        slot_id=s.slot_id,
                        name=s.name,
                        start_time=s.start_time,
                        end_time=s.end_time,
                        max_capacity=s.max_capacity,
                        booked_count=s.booked_count,
                        available_capacity=s.available_capacity,
                        is_blackout=s.is_blackout,
                        load_percentage=slot_load,
                    )
                )

            days_list.append(
                CapacityHeatmapDay(
                    date=current_date,
                    day_name=current_date.strftime("%A"),
                    total_capacity=total_cap,
                    total_booked=total_bk,
                    total_available=total_av,
                    overall_load_percentage=load_pct,
                    is_full_blackout=available_slots.is_full_day_blackout,
                    blackout_reason=available_slots.blackout_reason,
                    slots=slot_heatmap,
                )
            )

        return CapacityHeatmapResponse(
            start_date=start_date,
            end_date=end_date,
            total_days=days,
            days=days_list,
        )

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

        # 4. Check Day of week applicability
        day_abbr = schedule_in.schedule_date.strftime("%a").upper()
        app_days = [d.strip().upper() for d in (slot.applicable_days or "MON,TUE,WED,THU,FRI,SAT,SUN").split(",") if d.strip()]
        if day_abbr not in app_days:
            raise ValueError(f"Slot '{slot.name}' is not operational on {schedule_in.schedule_date.strftime('%A')}s.")

        # 5. Check Blackout Dates
        blackout_stmt = select(ScheduleBlackout).where(
            and_(
                cast(ScheduleBlackout.blackout_date, Date) == schedule_in.schedule_date,
                ScheduleBlackout.is_active == True,
            )
        )
        blackout_res = await session.execute(blackout_stmt)
        blackouts = blackout_res.scalars().all()
        for b in blackouts:
            if b.is_full_day or b.slot_id is None or b.slot_id == slot.id:
                raise ValueError(f"Scheduling is blocked on {schedule_in.schedule_date} due to: {b.reason}")

        # 6. Verify capacity for selected slot on target date
        booked_count = await self.get_slot_booked_count(session, slot.id, schedule_in.schedule_date)
        if booked_count >= slot.max_capacity:
            raise ValueError(f"Selected time slot '{slot.name}' on {schedule_in.schedule_date} is fully booked ({booked_count}/{slot.max_capacity}). Please choose another slot.")

        # 7. Format schedule code
        date_str = schedule_in.schedule_date.strftime("%Y%m%d")
        rand_suffix = secrets.token_hex(2).upper()
        schedule_code = f"SCH-{date_str}-{rand_suffix}"

        # 8. Construct DateTime from date
        schedule_dt = datetime.combine(schedule_in.schedule_date, time(0, 0))

        # 9. Create schedule object
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

