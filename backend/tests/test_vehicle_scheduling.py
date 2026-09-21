from datetime import date, datetime, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.meta import (
    ApplicationPhaseStatus,
    VehicleScheduleStatus,
    ScheduleComplianceStatus,
    UserRole,
)
from backend.schemas.request.schedule import VehicleScheduleCreate
from backend.schemas.request.application import NakaEntryCreate, NakaMaterialItem
from backend.dao.schedule import VehicleScheduleDAO
from backend.services.schedule import VehicleScheduleService
from backend.dbmodels.application import ApprovedApplicationPhase, VehicleSchedule, SlotDefinition


@pytest.mark.anyio
class TestVehicleScheduling:
    async def test_single_active_schedule_per_token_constraint(self):
        """Ensure a token cannot have two active schedules."""
        dao = VehicleScheduleDAO()
        mock_session = AsyncMock()

        # Mock token exists and is ACTIVE
        mock_token = MagicMock()
        mock_token.id = 1
        mock_token.application_id = 10
        mock_token.phase = 1
        mock_token.status = ApplicationPhaseStatus.ACTIVE

        # Setup mock queries
        # First query for token:
        token_res = MagicMock()
        token_res.scalar_one_or_none.return_value = mock_token

        # Query for existing active schedule: returns an existing active schedule
        mock_existing_schedule = MagicMock()
        mock_existing_schedule.id = 99
        mock_existing_schedule.schedule_code = "SCH-20260901-A1B2"
        mock_existing_schedule.schedule_date = datetime(2026, 9, 2)
        mock_existing_schedule.status = VehicleScheduleStatus.SCHEDULED

        # Mock get_active_schedule_by_token
        dao.get_active_schedule_by_token = AsyncMock(return_value=mock_existing_schedule)

        # Mock session.execute for token lookup
        mock_session.execute.return_value = token_res

        schedule_in = VehicleScheduleCreate(
            token_id=1,
            slot_id=2,
            schedule_date=date.today() + timedelta(days=2),
            vehicle_number="RJ 27 GA 1234",
        )

        with pytest.raises(ValueError) as exc_info:
            await dao.create_schedule(mock_session, user_id=5, schedule_in=schedule_in)

        assert "already exists for this token" in str(exc_info.value)

    async def test_slot_capacity_exhaustion(self):
        """Ensure booking fails when slot capacity is full."""
        dao = VehicleScheduleDAO()
        mock_session = AsyncMock()

        mock_token = MagicMock()
        mock_token.id = 1
        mock_token.application_id = 10
        mock_token.phase = 1
        mock_token.status = ApplicationPhaseStatus.ACTIVE

        token_res = MagicMock()
        token_res.scalar_one_or_none.return_value = mock_token

        mock_slot = MagicMock()
        mock_slot.id = 2
        mock_slot.name = "Slot 1 (08:00 AM - 10:00 AM)"
        mock_slot.max_capacity = 5
        mock_slot.applicable_days = "MON,TUE,WED,THU,FRI,SAT,SUN"
        mock_slot.is_active = True

        slot_res = MagicMock()
        slot_res.scalar_one_or_none.return_value = mock_slot

        blackout_res = MagicMock()
        blackout_res.scalars.return_value.all.return_value = []

        # Sequence of execute calls: 1. token lookup, 2. slot lookup, 3. blackout lookup
        mock_session.execute.side_effect = [token_res, slot_res, blackout_res]

        dao.get_active_schedule_by_token = AsyncMock(return_value=None)
        dao.get_slot_booked_count = AsyncMock(return_value=5)  # Max capacity reached

        schedule_in = VehicleScheduleCreate(
            token_id=1,
            slot_id=2,
            schedule_date=date.today() + timedelta(days=2),
            vehicle_number="RJ 27 GA 1234",
        )

        with pytest.raises(ValueError) as exc_info:
            await dao.create_schedule(mock_session, user_id=5, schedule_in=schedule_in)

        assert "fully booked" in str(exc_info.value)

    async def test_blackout_date_blocks_scheduling(self):
        """Ensure booking fails when date is marked as blackout holiday."""
        dao = VehicleScheduleDAO()
        mock_session = AsyncMock()

        mock_token = MagicMock()
        mock_token.id = 1
        mock_token.application_id = 10
        mock_token.phase = 1
        mock_token.status = ApplicationPhaseStatus.ACTIVE

        token_res = MagicMock()
        token_res.scalar_one_or_none.return_value = mock_token

        mock_slot = MagicMock()
        mock_slot.id = 2
        mock_slot.name = "Slot 1 (08:00 AM - 10:00 AM)"
        mock_slot.max_capacity = 20
        mock_slot.applicable_days = "MON,TUE,WED,THU,FRI,SAT,SUN"
        mock_slot.is_active = True

        slot_res = MagicMock()
        slot_res.scalar_one_or_none.return_value = mock_slot

        mock_blackout = MagicMock()
        mock_blackout.reason = "Mount Abu Summer Festival"
        mock_blackout.is_full_day = True
        mock_blackout.slot_id = None

        blackout_res = MagicMock()
        blackout_res.scalars.return_value.all.return_value = [mock_blackout]

        mock_session.execute.side_effect = [token_res, slot_res, blackout_res]
        dao.get_active_schedule_by_token = AsyncMock(return_value=None)

        schedule_in = VehicleScheduleCreate(
            token_id=1,
            slot_id=2,
            schedule_date=date.today() + timedelta(days=2),
            vehicle_number="RJ 27 GA 1234",
        )

        with pytest.raises(ValueError) as exc_info:
            await dao.create_schedule(mock_session, user_id=5, schedule_in=schedule_in)

        assert "Mount Abu Summer Festival" in str(exc_info.value)

    async def test_same_day_booking_rejected_t_plus_1(self):
        """Ensure booking fails when attempting same-day (T+0) or past bookings."""
        dao = VehicleScheduleDAO()
        mock_session = AsyncMock()

        schedule_in = VehicleScheduleCreate(
            token_id=1,
            slot_id=2,
            schedule_date=date.today(),
            vehicle_number="RJ 27 GA 1234",
        )

        with pytest.raises(ValueError) as exc_info:
            await dao.create_schedule(mock_session, user_id=5, schedule_in=schedule_in)

        assert "at least 1 day in advance (T+1 basis)" in str(exc_info.value)

    async def test_beyond_1_week_booking_rejected(self):
        """Ensure booking fails when attempting booking beyond 1 week (T+8 days)."""
        dao = VehicleScheduleDAO()
        mock_session = AsyncMock()

        schedule_in = VehicleScheduleCreate(
            token_id=1,
            slot_id=2,
            schedule_date=date.today() + timedelta(days=8),
            vehicle_number="RJ 27 GA 1234",
        )

        with pytest.raises(ValueError) as exc_info:
            await dao.create_schedule(mock_session, user_id=5, schedule_in=schedule_in)

        assert "up to 1 week in advance" in str(exc_info.value)


    async def test_naka_entry_requires_mandatory_remarks(self):
        """Ensure Naka entry validation requires remarks."""
        # Empty remarks should fail validation
        with pytest.raises(Exception):
            NakaEntryCreate(
                materials=[NakaMaterialItem(material_id=1, quantity_brought=5.0)],
                vehicle_number="RJ 27 GA 1234",
                remarks="",  # min_length=1
            )

        # Valid remarks pass
        entry = NakaEntryCreate(
            materials=[NakaMaterialItem(material_id=1, quantity_brought=5.0)],
            vehicle_number="RJ 27 GA 1234",
            remarks="Normal on-time material transit",
            schedule_compliance_status=ScheduleComplianceStatus.ON_TIME,
        )
        assert entry.remarks == "Normal on-time material transit"
        assert entry.schedule_compliance_status == ScheduleComplianceStatus.ON_TIME

    async def test_get_active_schedule_by_token_resolves_phase(self):
        """Ensure get_active_schedule_by_token looks up token phase before querying VehicleSchedule."""
        dao = VehicleScheduleDAO()
        mock_session = AsyncMock()

        mock_token = MagicMock(spec=ApprovedApplicationPhase)
        mock_token.id = 153
        mock_token.application_id = 42
        mock_token.phase = 2

        token_res = MagicMock()
        token_res.scalar_one_or_none.return_value = mock_token

        mock_schedule = MagicMock(spec=VehicleSchedule)
        mock_schedule.id = 10
        mock_schedule.application_id = 42
        mock_schedule.phase = 2
        mock_schedule.status = VehicleScheduleStatus.SCHEDULED

        sched_res = MagicMock()
        sched_res.scalar_one_or_none.return_value = mock_schedule

        mock_session.execute.side_effect = [token_res, sched_res]

        res = await dao.get_active_schedule_by_token(mock_session, token_id=153)
        assert res is not None
        assert res.id == 10
        assert mock_session.execute.call_count == 2

    async def test_blackout_auto_cancels_existing_schedules(self):
        """Ensure creating a blackout auto-cancels existing SCHEDULED bookings on that date."""
        from backend.dao.master import MasterDataDAO
        from backend.dbmodels.master import ScheduleBlackout
        from backend.schemas.request.master import ScheduleBlackoutCreate

        master_dao = MasterDataDAO()
        mock_session = AsyncMock()

        target_date = date.today() + timedelta(days=3)

        mock_schedule = MagicMock(spec=VehicleSchedule)
        mock_schedule.id = 55
        mock_schedule.vehicle_number = "RJ 27 GA 9999"
        mock_schedule.schedule_date = datetime.combine(target_date, datetime.min.time())
        mock_schedule.status = VehicleScheduleStatus.SCHEDULED
        mock_schedule.user = MagicMock()
        mock_schedule.user.mobile = "9876543210"

        res_sched = MagicMock()
        res_sched.scalars.return_value.all.return_value = [mock_schedule]
        mock_session.execute.return_value = res_sched

        blackout_obj = ScheduleBlackout(
            id=1,
            blackout_date=datetime.combine(target_date, datetime.min.time()),
            reason="Emergency Maintenance",
            is_full_day=True,
            slot_id=None,
            is_active=True,
        )

        with patch("backend.services.sms.sms_service.send_schedule_cancellation_sms", new_callable=AsyncMock) as mock_sms:
            cancelled_count = await master_dao._cancel_schedules_for_blackout(mock_session, blackout_obj)
            assert cancelled_count == 1
            assert mock_schedule.status == VehicleScheduleStatus.CANCELLED
            assert mock_schedule.cancelled_at is not None
            mock_sms.assert_awaited_once_with(
                mobile="9876543210",
                vehicle_number="RJ 27 GA 9999",
                schedule_date=str(target_date),
                reason="Emergency Maintenance",
            )



