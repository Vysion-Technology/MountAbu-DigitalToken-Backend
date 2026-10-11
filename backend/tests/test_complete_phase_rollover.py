import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from backend.dao.application import ApplicationDAO
from backend.dbmodels.application import (
    ApprovedApplicationPhase,
    ApplicationPhaseMaterial,
    VehicleEntry,
    VehicleMaterial,
)
from backend.meta import ApplicationPhaseStatus


class TestCompletePhaseRollover(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_session = AsyncMock()
        self.dao = ApplicationDAO(self.mock_session)

    async def test_complete_phase_with_rollover(self):
        """Phase 1 has 100 cement, 60 consumed. 40 should roll over to Phase 2."""
        app_id = 1
        phase_1 = 1
        user_id = 10

        # Phase 1 record
        phase_rec = MagicMock(spec=ApprovedApplicationPhase)
        phase_rec.id = 101
        phase_rec.application_id = app_id
        phase_rec.phase = 1
        phase_rec.status = ApplicationPhaseStatus.ACTIVE
        phase_rec.completed_at = None

        # Next phase record (Phase 2, in PENDING)
        next_phase_rec = MagicMock(spec=ApprovedApplicationPhase)
        next_phase_rec.id = 102
        next_phase_rec.application_id = app_id
        next_phase_rec.phase = 2
        next_phase_rec.status = ApplicationPhaseStatus.PENDING

        # Phase 1 material: 100 cement (material_id=5)
        cur_mat = MagicMock(spec=ApplicationPhaseMaterial)
        cur_mat.application_id = app_id
        cur_mat.phase = 1
        cur_mat.material_id = 5
        cur_mat.custom_name = "Cement"
        cur_mat.custom_unit = "Bags"
        cur_mat.quantity = 100

        # Phase 2 material: already has 50 cement
        next_mat = MagicMock(spec=ApplicationPhaseMaterial)
        next_mat.application_id = app_id
        next_mat.phase = 2
        next_mat.material_id = 5
        next_mat.custom_name = "Cement"
        next_mat.custom_unit = "Bags"
        next_mat.quantity = 50

        # Consumed row: 60 cement brought in
        consumed_row = MagicMock()
        consumed_row.material_id = 5
        consumed_row.custom_name = "Cement"
        consumed_row.total_brought = 60.0

        async def mock_execute(stmt):
            res = MagicMock()
            params = stmt.compile().params
            sql_str = str(stmt).lower()
            if "vehicle_materials" in sql_str and "coalesce" in sql_str:
                res.__iter__ = MagicMock(return_value=iter([consumed_row]))
                return res
            elif "application_phase_materials" in sql_str:
                if params.get("phase_1") == 1:
                    res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[cur_mat])))
                else:
                    res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[next_mat])))
                return res
            elif "applications.num_stages" in sql_str or "applications" in sql_str and "num_stages" in sql_str:
                res.scalar = MagicMock(return_value=2)
                return res
            elif "application_phases" in sql_str:
                if params.get("phase_1") == 1:
                    res.scalar_one_or_none = MagicMock(return_value=phase_rec)
                else:
                    res.scalar_one_or_none = MagicMock(return_value=next_phase_rec)
                return res
            return res

        self.mock_session.execute = AsyncMock(side_effect=mock_execute)

        response = await self.dao.complete_phase(
            application_id=app_id,
            phase_num=phase_1,
            user_id=user_id,
        )

        self.assertIn("completed successfully", response.message)
        self.assertEqual(phase_rec.status, ApplicationPhaseStatus.COMPLETED)
        # Next phase material should now have 50 + (100 - 60) = 90
        self.assertEqual(next_mat.quantity, 90)
        # Current phase allocation should be adjusted to 60 consumed
        self.assertEqual(cur_mat.quantity, 60)
        self.mock_session.commit.assert_awaited_once()

    async def test_complete_phase_already_completed(self):
        """Raises 400 if phase is already COMPLETED."""
        app_id = 1
        phase_1 = 1
        user_id = 10

        phase_rec = MagicMock(spec=ApprovedApplicationPhase)
        phase_rec.status = ApplicationPhaseStatus.COMPLETED

        mock_res = MagicMock()
        mock_res.scalar_one_or_none = MagicMock(return_value=phase_rec)
        self.mock_session.execute = AsyncMock(return_value=mock_res)

        with self.assertRaises(HTTPException) as ctx:
            await self.dao.complete_phase(app_id, phase_1, user_id)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("already COMPLETED", ctx.exception.detail)
