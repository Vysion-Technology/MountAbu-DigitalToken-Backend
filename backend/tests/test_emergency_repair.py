import unittest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from backend.dao.application import ApplicationDAO
from backend.dbmodels.application import Application, ApprovedApplicationPhase
from backend.meta import (
    ApplicationStatus,
    ApplicationType,
    ApplicationFlags,
    PropertyUsageType,
    UserRole,
    WorkflowAction,
)
from backend.schemas.request.application import ApplicationCreate


class TestEmergencyRepairAndJenSkip(unittest.IsolatedAsyncioTestCase):
    def test_emergency_repair_schema_validation(self):
        # RENOVATION with is_emergency_repair = True should keep True
        app_renovation = ApplicationCreate(
            applicant_name="John Doe",
            father_name="Father Doe",
            current_address="Current Address",
            property_address="Property Address",
            title="Emergency Roof Repair",
            work_description="Urgent repair for damaged roof due to heavy rains",
            is_agriculture_land=False,
            property_usage=PropertyUsageType.DOMESTIC,
            ward_id=1,
            type=ApplicationType.RENOVATION,
            is_emergency_repair=True,
        )
        self.assertTrue(app_renovation.is_emergency_repair)

        # NEW with is_emergency_repair = True should reset to False
        app_new = ApplicationCreate(
            applicant_name="John Doe",
            father_name="Father Doe",
            current_address="Current Address",
            property_address="Property Address",
            title="New House",
            work_description="New building construction",
            is_agriculture_land=False,
            property_usage=PropertyUsageType.DOMESTIC,
            ward_id=1,
            type=ApplicationType.NEW,
            is_emergency_repair=True,
        )
        self.assertFalse(app_new.is_emergency_repair)

    async def test_renovation_direct_approval_disallowed_for_regular_application(self):
        mock_session = AsyncMock()
        dao = ApplicationDAO(mock_session)

        mock_app = MagicMock(spec=Application)
        mock_app.id = 1
        mock_app.type = ApplicationType.RENOVATION
        mock_app.status = ApplicationStatus.SUBMITTED
        mock_app.property_usage = PropertyUsageType.DOMESTIC
        mock_app.is_emergency_repair = False
        mock_app.comments = []
        mock_app.inspections = []
        mock_app.phase_materials = []
        mock_app.phases = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_app
        mock_session.execute = AsyncMock(return_value=mock_result)

        with self.assertRaises(HTTPException) as ctx:
            await dao.perform_workflow_action(
                application_id=1,
                action=WorkflowAction.APPROVE,
                user_id=10,
                user_role=UserRole.NODAL_OFFICER,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Only Government or Emergency Repair", ctx.exception.detail)

    async def test_renovation_direct_approval_allowed_for_emergency_repair(self):
        mock_session = AsyncMock()
        dao = ApplicationDAO(mock_session)

        mock_app = MagicMock(spec=Application)
        mock_app.id = 2
        mock_app.type = ApplicationType.RENOVATION
        mock_app.status = ApplicationStatus.SUBMITTED
        mock_app.property_usage = PropertyUsageType.DOMESTIC
        mock_app.is_emergency_repair = True
        mock_app.comments = []
        mock_app.inspections = []
        mock_app.phase_materials = []
        mock_app.phases = []
        mock_app.created_at = None
        mock_app.mobile = "9876543210"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_app
        mock_session.execute = AsyncMock(return_value=mock_result)

        response = await dao.perform_workflow_action(
            application_id=2,
            action=WorkflowAction.APPROVE,
            user_id=10,
            user_role=UserRole.NODAL_OFFICER,
        )
        self.assertEqual(response.message, "Application approved successfully")
        self.assertEqual(mock_app.status, ApplicationStatus.APPROVED)

    async def test_renovation_direct_approval_allowed_for_government(self):
        mock_session = AsyncMock()
        dao = ApplicationDAO(mock_session)

        mock_app = MagicMock(spec=Application)
        mock_app.id = 3
        mock_app.type = ApplicationType.RENOVATION
        mock_app.status = ApplicationStatus.SUBMITTED
        mock_app.property_usage = PropertyUsageType.GOVERNMENT
        mock_app.is_emergency_repair = False
        mock_app.comments = []
        mock_app.inspections = []
        mock_app.phase_materials = []
        mock_app.phases = []
        mock_app.created_at = None
        mock_app.mobile = "9876543210"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_app
        mock_session.execute = AsyncMock(return_value=mock_result)

        response = await dao.perform_workflow_action(
            application_id=3,
            action=WorkflowAction.APPROVE,
            user_id=10,
            user_role=UserRole.NODAL_OFFICER,
        )
        self.assertEqual(response.message, "Application approved successfully")
        self.assertEqual(mock_app.status, ApplicationStatus.APPROVED)

    async def test_generate_tokens_skips_jen_for_emergency_and_gov(self):
        mock_session = AsyncMock()
        dao = ApplicationDAO(mock_session)

        # 1. Emergency Repair Renovation: no inspections, but can generate tokens
        mock_app = MagicMock(spec=Application)
        mock_app.id = 4
        mock_app.type = ApplicationType.RENOVATION
        mock_app.status = ApplicationStatus.APPROVED
        mock_app.property_usage = PropertyUsageType.DOMESTIC
        mock_app.is_emergency_repair = True
        mock_app.inspections = []  # No inspections!
        mock_app.phases = []
        mock_app.phase_materials = []
        mock_app.num_stages = 1
        mock_app.created_at = None
        mock_app.mobile = "9876543210"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_app
        mock_session.execute = AsyncMock(return_value=mock_result)

        response = await dao.perform_workflow_action(
            application_id=4,
            action=WorkflowAction.GENERATE_TOKENS,
            user_id=10,
            user_role=UserRole.NODAL_OFFICER,
            phase=1,
        )
        self.assertEqual(response.message, "Application generate_tokensd successfully")
        self.assertEqual(mock_app.status, ApplicationStatus.TOKEN_GENERATED)

        # 2. Regular Renovation: no inspections -> should fail
        mock_app_reg = MagicMock(spec=Application)
        mock_app_reg.id = 5
        mock_app_reg.type = ApplicationType.RENOVATION
        mock_app_reg.status = ApplicationStatus.APPROVED
        mock_app_reg.property_usage = PropertyUsageType.DOMESTIC
        mock_app_reg.is_emergency_repair = False
        mock_app_reg.inspections = []  # No inspections
        mock_app_reg.phases = []

        mock_result_reg = MagicMock()
        mock_result_reg.scalar_one_or_none.return_value = mock_app_reg
        mock_session.execute = AsyncMock(return_value=mock_result_reg)

        with self.assertRaises(HTTPException) as ctx:
            await dao.perform_workflow_action(
                application_id=5,
                action=WorkflowAction.GENERATE_TOKENS,
                user_id=10,
                user_role=UserRole.NODAL_OFFICER,
                phase=1,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("JEN inspection must be completed", ctx.exception.detail)

    def test_flags_and_pending_with_me(self):
        dao = ApplicationDAO(AsyncMock())

        # Emergency renovation in SUBMITTED
        app = MagicMock(spec=Application)
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.SUBMITTED
        app.property_usage = PropertyUsageType.DOMESTIC
        app.is_emergency_repair = True
        app.objection_to_role = None

        flags_nodal = dao.get_required_flags(app, UserRole.NODAL_OFFICER)
        self.assertIn(ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_ACTION, flags_nodal)
        self.assertIn(ApplicationFlags.PENDING_WITH_ME, flags_nodal)
