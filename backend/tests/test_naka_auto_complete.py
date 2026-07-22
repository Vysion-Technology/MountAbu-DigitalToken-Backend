import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from sqlalchemy.sql import select

from backend.dao.application import ApplicationDAO
from backend.dbmodels.application import (
    Application,
    ApprovedApplicationPhase,
    ApplicationPhaseMaterial,
)
from backend.meta import ApplicationStatus, ApplicationPhaseStatus, WorkflowAction
from backend.schemas.request.application import NakaMaterialItem


class TestNakaAutoComplete(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_session = AsyncMock()
        self.dao = ApplicationDAO(self.mock_session)

    async def test_naka_entry_fully_exhausted_auto_completes_phase(self):
        """Phase auto-completes when total brought matches/exceeds allocated quantity."""
        app_id = 1
        phase_num = 1
        user_id = 42

        # Mock application
        mock_app = MagicMock(spec=Application)
        mock_app.status = ApplicationStatus.TOKEN_GENERATED
        self.mock_session.get.return_value = mock_app

        # Mock phase
        mock_phase = MagicMock(spec=ApprovedApplicationPhase)
        mock_phase.status = ApplicationPhaseStatus.ACTIVE
        mock_phase.completed_at = None

        # Mock phase material (allocated: 10 units)
        mock_phase_mat = MagicMock(spec=ApplicationPhaseMaterial)
        mock_phase_mat.material_id = 5
        mock_phase_mat.custom_name = None
        mock_phase_mat.quantity = 10

        # Create input materials for the entry
        mat_item = NakaMaterialItem(
            material_id=5,
            quantity_brought=5.0
        )

        # We will mock the DB calls:
        # 1. First execute: query phase -> returns mock_phase
        # 2. Second execute: query phase material in loop -> returns mock_phase_mat
        # 3. Third execute: query existing sum (already brought: 5) -> returns 5
        # 4. Fourth execute: query all phase materials -> returns [mock_phase_mat]
        # 5. Fifth execute: query total sum for completion check (total brought: 10) -> returns 10
        execute_counter = 0

        async def mock_execute(stmt):
            nonlocal execute_counter
            sql_str = str(stmt)
            res = MagicMock()
            
            if "application_phases" in sql_str:
                res.scalar_one_or_none = MagicMock(return_value=mock_phase)
            elif "application_phase_materials" in sql_str:
                res.scalar_one_or_none = MagicMock(return_value=mock_phase_mat)
                res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_phase_mat])))
            elif "sum" in sql_str or "coalesce" in sql_str:
                # First sum query (inside validation loop, before adding the new 5 units): returns 5
                # Second sum query (inside completion loop, after flush, including new 5 units): returns 10
                if execute_counter < 3:
                    res.scalar = MagicMock(return_value=5.0)
                else:
                    res.scalar = MagicMock(return_value=10.0)
            
            execute_counter += 1
            return res

        self.mock_session.execute = AsyncMock(side_effect=mock_execute)
        self.mock_session.flush = AsyncMock()
        self.mock_session.commit = AsyncMock()
        self.mock_session.add = MagicMock()

        # Run
        response = await self.dao.create_naka_entry(
            application_id=app_id,
            phase=phase_num,
            user_id=user_id,
            materials=[mat_item.model_dump()],
            vehicle_number="KA-01-1234",
            vehicle_type="Truck"
        )

        # Verify
        self.assertEqual(response.message, "Naka entry recorded successfully")
        self.assertEqual(mock_phase.status, ApplicationPhaseStatus.COMPLETED)
        self.assertIsNotNone(mock_phase.completed_at)
        self.mock_session.commit.assert_awaited_once()

    async def test_naka_entry_partially_exhausted_remains_active(self):
        """Phase remains ACTIVE if there is still allocated material quantity remaining."""
        app_id = 1
        phase_num = 1
        user_id = 42

        # Mock application
        mock_app = MagicMock(spec=Application)
        mock_app.status = ApplicationStatus.TOKEN_GENERATED
        self.mock_session.get.return_value = mock_app

        # Mock phase
        mock_phase = MagicMock(spec=ApprovedApplicationPhase)
        mock_phase.status = ApplicationPhaseStatus.ACTIVE
        mock_phase.completed_at = None

        # Mock phase material (allocated: 10 units)
        mock_phase_mat = MagicMock(spec=ApplicationPhaseMaterial)
        mock_phase_mat.material_id = 5
        mock_phase_mat.custom_name = None
        mock_phase_mat.quantity = 10

        # Create input materials for the entry
        mat_item = NakaMaterialItem(
            material_id=5,
            quantity_brought=2.0
        )

        execute_counter = 0

        async def mock_execute(stmt):
            nonlocal execute_counter
            sql_str = str(stmt)
            res = MagicMock()
            
            if "application_phases" in sql_str:
                res.scalar_one_or_none = MagicMock(return_value=mock_phase)
            elif "application_phase_materials" in sql_str:
                res.scalar_one_or_none = MagicMock(return_value=mock_phase_mat)
                res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_phase_mat])))
            elif "sum" in sql_str or "coalesce" in sql_str:
                # First sum query (inside validation loop): returns 5
                # Second sum query (inside completion loop, total brought is now 7): returns 7
                if execute_counter < 3:
                    res.scalar = MagicMock(return_value=5.0)
                else:
                    res.scalar = MagicMock(return_value=7.0)
            
            execute_counter += 1
            return res

        self.mock_session.execute = AsyncMock(side_effect=mock_execute)
        self.mock_session.flush = AsyncMock()
        self.mock_session.commit = AsyncMock()
        self.mock_session.add = MagicMock()

        # Run
        response = await self.dao.create_naka_entry(
            application_id=app_id,
            phase=phase_num,
            user_id=user_id,
            materials=[mat_item.model_dump()],
            vehicle_number="KA-01-1234",
            vehicle_type="Truck"
        )

        # Verify
        self.assertEqual(response.message, "Naka entry recorded successfully")
        self.assertEqual(mock_phase.status, ApplicationPhaseStatus.ACTIVE)
        self.assertIsNone(mock_phase.completed_at)
        self.mock_session.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
