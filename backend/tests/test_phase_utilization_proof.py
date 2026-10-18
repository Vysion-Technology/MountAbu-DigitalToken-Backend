import unittest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from backend.dao.application import ApplicationDAO
from backend.dbmodels.application import (
    Application,
    ApprovedApplicationPhase,
    PhaseUtilizationProof,
)
from backend.meta import (
    ApplicationStatus,
    ApplicationPhaseStatus,
    ApplicationType,
    UserRole,
    WorkflowAction,
)
from backend.schemas.request.application import PhaseUtilizationProofCreate


class TestPhaseUtilizationProof(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_session = AsyncMock()
        self.dao = ApplicationDAO(self.mock_session)

        self.mock_app = MagicMock(spec=Application)
        self.mock_app.id = 1
        self.mock_app.status = ApplicationStatus.TOKEN_GENERATED
        self.mock_app.type = ApplicationType.NEW
        self.mock_app.num_stages = 2
        self.mock_app.phases = []
        self.mock_app.utilization_proofs = []
        self.mock_app.inspections = [MagicMock()]

        # Setup mock execute returning mock_app on application queries
        async def mock_execute(stmt):
            sql_str = str(stmt).lower()
            res = MagicMock()
            if "from applications" in sql_str or "where applications.id" in sql_str:
                res.scalar_one_or_none = MagicMock(return_value=self.mock_app)
                res.scalar_one = MagicMock(return_value=self.mock_app)
            elif "from phase_utilization_proofs" in sql_str:
                # Return proof if any in mock_app
                proof = self.mock_app.utilization_proofs[0] if self.mock_app.utilization_proofs else None
                res.scalar_one_or_none = MagicMock(return_value=proof)
                res.scalar_one = MagicMock(return_value=proof)
            elif "from application_phases" in sql_str:
                res.scalar_one_or_none = MagicMock(return_value=self.mock_app.phases[0] if self.mock_app.phases else None)
                res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=self.mock_app.phases)))
            else:
                res.scalar_one_or_none = MagicMock(return_value=None)
                res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            return res

        self.mock_session.execute = AsyncMock(side_effect=mock_execute)

    async def test_cannot_generate_phase_2_without_phase_1_proof(self):
        """Next token generation is blocked if previous completed phase has no utilization proof."""
        phase_1 = MagicMock(spec=ApprovedApplicationPhase)
        phase_1.phase = 1
        phase_1.status = ApplicationPhaseStatus.COMPLETED
        self.mock_app.phases = [phase_1]
        self.mock_app.utilization_proofs = []

        with self.assertRaises(HTTPException) as ctx:
            await self.dao.perform_workflow_action(
                application_id=1,
                action=WorkflowAction.GENERATE_TOKENS,
                user_id=10,
                user_role=UserRole.NODAL_OFFICER,
                phase=2,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Utilization proof", ctx.exception.detail)

    async def test_can_generate_phase_2_with_phase_1_proof(self):
        """Next token generation succeeds when previous phase utilization proof is present."""
        phase_1 = MagicMock(spec=ApprovedApplicationPhase)
        phase_1.phase = 1
        phase_1.status = ApplicationPhaseStatus.COMPLETED
        self.mock_app.phases = [phase_1]

        mock_proof = MagicMock(spec=PhaseUtilizationProof)
        mock_proof.id = 1
        mock_proof.phase = 1
        mock_proof.photos = ["photos/site1.jpg"]
        mock_proof.submitted_by = MagicMock(name="Applicant Citizen")
        self.mock_app.utilization_proofs = [mock_proof]

        response = await self.dao.perform_workflow_action(
            application_id=1,
            action=WorkflowAction.GENERATE_TOKENS,
            user_id=10,
            user_role=UserRole.NODAL_OFFICER,
            phase=2,
        )

        self.assertEqual(response.message, "Application generate_tokensd successfully")
        self.mock_session.commit.assert_awaited_once()

    async def test_submit_phase_utilization_proof(self):
        """Submitting utilization proof creates proof and logs action."""
        phase_1 = MagicMock(spec=ApprovedApplicationPhase)
        phase_1.phase = 1
        phase_1.status = ApplicationPhaseStatus.COMPLETED
        self.mock_app.phases = [phase_1]

        proof_data = PhaseUtilizationProofCreate(
            work_completion_details="Completed foundation and 50% wall construction",
            completion_percentage=50,
            declaration_accepted=True,
            photos=["apps/1/phase1_foundation.jpg"],
        )

        # Mock the newly created proof when re-fetched
        created_proof = MagicMock(spec=PhaseUtilizationProof)
        created_proof.id = 101
        created_proof.application_id = 1
        created_proof.phase = 1
        created_proof.work_completion_details = proof_data.work_completion_details
        created_proof.completion_percentage = 50
        created_proof.declaration_accepted = True
        created_proof.remarks = None
        created_proof.photos = proof_data.photos
        created_proof.submitted_by_id = 5
        created_proof.submitted_by = MagicMock()
        created_proof.submitted_by.name = "Test Citizen"
        created_proof.submitted_at = MagicMock()

        async def execute_side_effect(stmt):
            sql_str = str(stmt).lower()
            res = MagicMock()
            if "from applications" in sql_str:
                res.scalar_one_or_none = MagicMock(return_value=self.mock_app)
            elif "from phase_utilization_proofs" in sql_str:
                # First check is existing proof (returns None), second check is full_proof (returns created_proof)
                if hasattr(self, "_checked_proof"):
                    res.scalar_one = MagicMock(return_value=created_proof)
                else:
                    self._checked_proof = True
                    res.scalar_one_or_none = MagicMock(return_value=None)
            return res

        self.mock_session.execute = AsyncMock(side_effect=execute_side_effect)

        result = await self.dao.submit_phase_utilization_proof(
            application_id=1,
            phase_num=1,
            user_id=5,
            data=proof_data,
        )

        self.assertEqual(result.work_completion_details, proof_data.work_completion_details)
        self.assertEqual(result.completion_percentage, 50)
        self.mock_session.commit.assert_awaited_once()
