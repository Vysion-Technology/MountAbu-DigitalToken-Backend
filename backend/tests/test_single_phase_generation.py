import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from backend.dao.application import ApplicationDAO
from backend.dbmodels.application import (
    Application,
    ApprovedApplicationPhase,
    InspectionReport,
)
from backend.meta import (
    ApplicationStatus,
    ApplicationPhaseStatus,
    ApplicationType,
    UserRole,
    WorkflowAction,
)


class TestSinglePhaseGeneration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_session = AsyncMock()
        self.dao = ApplicationDAO(self.mock_session)

        # Setup base mock application
        self.mock_app = MagicMock(spec=Application)
        self.mock_app.status = ApplicationStatus.APPROVED
        self.mock_app.type = ApplicationType.NEW
        self.mock_app.inspections = [MagicMock(spec=InspectionReport)]
        self.mock_app.phases = []
        self.mock_app.num_stages = 0

        self.mock_session.get.return_value = self.mock_app

        # Mock execute
        async def default_execute(stmt):
            sql_str = str(stmt)
            res = MagicMock()
            if "applications" in sql_str:
                res.scalar_one_or_none = MagicMock(return_value=self.mock_app)
            else:
                res.scalar_one_or_none = MagicMock(return_value=None)
            res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            return res

        self.mock_session.execute = AsyncMock(side_effect=default_execute)
        self.mock_session.commit = AsyncMock()
        self.mock_session.add = MagicMock()

    async def test_generate_phase_1_successfully(self):
        """Generating Phase 1 succeeds when no phases exist and sets it to ACTIVE."""
        response = await self.dao.perform_workflow_action(
            application_id=1,
            action=WorkflowAction.GENERATE_TOKENS,
            user_id=10,
            user_role=UserRole.NODAL_OFFICER,
            phase=1,
        )

        self.assertEqual(response.message, "Application generate_tokensd successfully")
        self.assertEqual(self.mock_app.status, ApplicationStatus.TOKEN_GENERATED)
        self.mock_session.commit.assert_awaited_once()

    async def test_generate_phase_2_without_phase_1_fails(self):
        """Generating Phase 2 fails if Phase 1 has not been generated yet."""
        with self.assertRaises(HTTPException) as ctx:
            await self.dao.perform_workflow_action(
                application_id=1,
                action=WorkflowAction.GENERATE_TOKENS,
                user_id=10,
                user_role=UserRole.NODAL_OFFICER,
                phase=2,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Phase 1 has not been generated yet", ctx.exception.detail)

    async def test_generate_phase_2_when_phase_1_is_active_fails(self):
        """Generating Phase 2 fails if Phase 1 is still ACTIVE (not COMPLETED)."""
        phase_1 = MagicMock(spec=ApprovedApplicationPhase)
        phase_1.phase = 1
        phase_1.status = ApplicationPhaseStatus.ACTIVE
        self.mock_app.phases = [phase_1]

        with self.assertRaises(HTTPException) as ctx:
            await self.dao.perform_workflow_action(
                application_id=1,
                action=WorkflowAction.GENERATE_TOKENS,
                user_id=10,
                user_role=UserRole.NODAL_OFFICER,
                phase=2,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("must be COMPLETED", ctx.exception.detail)

    async def test_generate_phase_2_when_phase_1_is_completed_succeeds(self):
        """Generating Phase 2 succeeds if Phase 1 status is COMPLETED."""
        phase_1 = MagicMock(spec=ApprovedApplicationPhase)
        phase_1.phase = 1
        phase_1.status = ApplicationPhaseStatus.COMPLETED
        self.mock_app.phases = [phase_1]

        response = await self.dao.perform_workflow_action(
            application_id=1,
            action=WorkflowAction.GENERATE_TOKENS,
            user_id=10,
            user_role=UserRole.NODAL_OFFICER,
            phase=2,
        )

        self.assertEqual(response.message, "Application generate_tokensd successfully")
        self.assertEqual(self.mock_app.status, ApplicationStatus.TOKEN_GENERATED)
        self.mock_session.commit.assert_awaited_once()

    async def test_generate_duplicate_phase_fails(self):
        """Generating Phase 1 fails if Phase 1 has already been generated."""
        phase_1 = MagicMock(spec=ApprovedApplicationPhase)
        phase_1.phase = 1
        phase_1.status = ApplicationPhaseStatus.ACTIVE
        self.mock_app.phases = [phase_1]

        with self.assertRaises(HTTPException) as ctx:
            await self.dao.perform_workflow_action(
                application_id=1,
                action=WorkflowAction.GENERATE_TOKENS,
                user_id=10,
                user_role=UserRole.NODAL_OFFICER,
                phase=1,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Phase 1 has already been generated", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
