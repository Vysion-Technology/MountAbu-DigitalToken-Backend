from datetime import date
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dao.schedule import VehicleScheduleDAO
from backend.dbmodels.application import VehicleSchedule
from backend.core.transport_code import encode_transport_code
from backend.schemas.request.schedule import VehicleScheduleCreate
from backend.schemas.response.schedule import (
    AvailableSlotsResponse,
    VehicleScheduleResponse,
    TokenScheduleStatusResponse,
    CapacityHeatmapResponse,
)



class VehicleScheduleService:
    def __init__(self):
        self.schedule_dao = VehicleScheduleDAO()

    def _to_response(self, schedule: VehicleSchedule) -> VehicleScheduleResponse:
        """Helper to transform ORM VehicleSchedule to Pydantic response."""
        slot_name = schedule.slot.name if schedule.slot else None
        start_time = schedule.slot.start_time if schedule.slot else None
        end_time = schedule.slot.end_time if schedule.slot else None
        vehicle_type_name = schedule.vehicle_type.name if schedule.vehicle_type else None
        property_address = (
            schedule.application.property_address if schedule.application else None
        )
        transport_code = encode_transport_code(schedule.application_id, schedule.phase)

        return VehicleScheduleResponse(
            id=schedule.id,
            schedule_code=schedule.schedule_code,
            application_id=schedule.application_id,
            token_id=schedule.token_id if hasattr(schedule, "token_id") and schedule.token_id else 0,
            phase=schedule.phase,
            user_id=schedule.user_id,
            slot_id=schedule.slot_id,
            slot_name=slot_name,
            start_time=start_time,
            end_time=end_time,
            schedule_date=schedule.schedule_date,
            vehicle_number=schedule.vehicle_number,
            vehicle_type_id=schedule.vehicle_type_id,
            vehicle_type_name=vehicle_type_name,
            status=schedule.status,
            created_at=schedule.created_at,
            cancelled_at=schedule.cancelled_at,
            transport_code=transport_code,
            property_address=property_address,
        )

    async def get_available_slots(
        self, session: AsyncSession, target_date: date
    ) -> AvailableSlotsResponse:
        return await self.schedule_dao.get_available_slots_for_date(session, target_date)

    async def book_schedule(
        self, session: AsyncSession, user_id: int, schedule_in: VehicleScheduleCreate
    ) -> VehicleScheduleResponse:
        db_schedule = await self.schedule_dao.create_schedule(session, user_id, schedule_in)
        return self._to_response(db_schedule)

    async def get_my_schedules(
        self, session: AsyncSession, user_id: int
    ) -> List[VehicleScheduleResponse]:
        schedules = await self.schedule_dao.get_schedules_by_user(session, user_id)
        return [self._to_response(s) for s in schedules]

    async def get_schedule_by_id(
        self, session: AsyncSession, schedule_id: int
    ) -> Optional[VehicleScheduleResponse]:
        s = await self.schedule_dao.get_schedule_by_id(session, schedule_id)
        if not s:
            return None
        return self._to_response(s)

    async def get_token_schedule_status(
        self, session: AsyncSession, token_id: int
    ) -> TokenScheduleStatusResponse:
        active = await self.schedule_dao.get_active_schedule_by_token(session, token_id)
        if not active:
            return TokenScheduleStatusResponse(has_active_schedule=False, active_schedule=None)
        return TokenScheduleStatusResponse(
            has_active_schedule=True, active_schedule=self._to_response(active)
        )

    async def get_capacity_heatmap(
        self, session: AsyncSession, start_date: date, days: int = 14
    ) -> CapacityHeatmapResponse:
        return await self.schedule_dao.get_capacity_heatmap(session, start_date, days)

    async def cancel_schedule(
        self, session: AsyncSession, schedule_id: int, user_id: int
    ) -> VehicleScheduleResponse:
        cancelled = await self.schedule_dao.cancel_schedule(session, schedule_id, user_id)
        return self._to_response(cancelled)

