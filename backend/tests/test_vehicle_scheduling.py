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
            schedule_date=date(2026, 9, 3),
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
            schedule_date=date(2026, 9, 3),
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
            schedule_date=date(2026, 9, 3),
            vehicle_number="RJ 27 GA 1234",
        )

        with pytest.raises(ValueError) as exc_info:
            await dao.create_schedule(mock_session, user_id=5, schedule_in=schedule_in)

        assert "Mount Abu Summer Festival" in str(exc_info.value)

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

