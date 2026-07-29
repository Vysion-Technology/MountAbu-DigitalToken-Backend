import unittest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from backend.dao.application import ApplicationDAO
from backend.dbmodels.application import Application, ApplicationObjection
from backend.meta import (
    ApplicationStatus,
    ApplicationType,
    UserRole,
    WorkflowAction,
    ObjectionStatus,
)

class TestNodalToCommissionerObjection(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_session = AsyncMock()
        self.dao = ApplicationDAO(self.mock_session)

        # Setup base mock application
        self.mock_app = MagicMock(spec=Application)
        self.mock_app.id = 1
        self.mock_app.status = ApplicationStatus.APPROVED
        self.mock_app.type = ApplicationType.NEW
        self.mock_app.objections = []
        self.mock_app.objected_from_status = None
        self.mock_app.objection_to_role = None

        self.mock_session.get.return_value = self.mock_app

        # Mock session execute responses
        async def default_execute(stmt):
            res = MagicMock()
            res.scalar_one_or_none = MagicMock(return_value=self.mock_app)
            res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            return res

        self.mock_session.execute = AsyncMock(side_effect=default_execute)
        self.mock_session.commit = AsyncMock()
        self.mock_session.add = MagicMock()

    async def test_nodal_officer_can_object_to_commissioner(self):
        """Nodal Officer should be allowed to raise an objection to the Commissioner."""
        await self.dao.perform_workflow_action(
            application_id=1,
            action=WorkflowAction.OBJECT,
            user_id=10,
            user_role=UserRole.NODAL_OFFICER,
            objection_to_roles=[UserRole.COMMISSIONER],
            remarks="Commissioner review needed",
        )

        # Ensure object_to_role was set to COMMISSIONER
        self.assertEqual(self.mock_app.objection_to_role, UserRole.COMMISSIONER)
        self.assertEqual(self.mock_app.status, ApplicationStatus.OBJECTED)

    async def test_other_roles_cannot_object_to_commissioner(self):
        """Commissioner should not be allowed to object to themselves on a renovation app in forwarded status."""
        self.mock_app.type = ApplicationType.RENOVATION
        self.mock_app.status = ApplicationStatus.FORWARDED
        self.mock_app.comments = []
        self.mock_app.inspections = []

        with self.assertRaises(HTTPException) as context:
            await self.dao.perform_workflow_action(
                application_id=1,
                action=WorkflowAction.OBJECT,
                user_id=20,
                user_role=UserRole.COMMISSIONER,
                objection_to_roles=[UserRole.COMMISSIONER],
                remarks="Not allowed",
            )
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Only Nodal Officer can raise an objection to the Commissioner", context.exception.detail)

    async def test_only_nodal_officer_can_clear_commissioner_objection(self):
        """Only Nodal Officer (or Superadmin) can clear objections sent to the Commissioner (using renovation app to pass workflow checks)."""
        self.mock_app.type = ApplicationType.RENOVATION
        self.mock_app.status = ApplicationStatus.OBJECTED

        # Setup application with a pending objection to Commissioner
        pending_obj = MagicMock(spec=ApplicationObjection)
        pending_obj.status = ObjectionStatus.PENDING
        pending_obj.objected_to_role = UserRole.COMMISSIONER
        self.mock_app.objections = [pending_obj]

        # Commissioner tries to clear the objection
        with self.assertRaises(HTTPException) as context:
            await self.dao.perform_workflow_action(
                application_id=1,
                action=WorkflowAction.CLEAR_OBJECTION,
                user_id=20,
                user_role=UserRole.COMMISSIONER,
                clear_objection_role=UserRole.COMMISSIONER,
            )
        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("Only Nodal Officer can verify and clear objections sent to the Commissioner", context.exception.detail)

        # Nodal Officer clearing the objection
        await self.dao.perform_workflow_action(
            application_id=1,
            action=WorkflowAction.CLEAR_OBJECTION,
            user_id=10,
            user_role=UserRole.NODAL_OFFICER,
            clear_objection_role=UserRole.COMMISSIONER,
        )

        self.assertEqual(pending_obj.status, ObjectionStatus.RESOLVED)

    async def test_nodal_officer_can_object_to_commissioner_in_submitted_state(self):
        """Nodal Officer should be allowed to raise an objection to the Commissioner in SUBMITTED state for new construction."""
        self.mock_app.type = ApplicationType.NEW
        self.mock_app.status = ApplicationStatus.SUBMITTED

        await self.dao.perform_workflow_action(
            application_id=1,
            action=WorkflowAction.OBJECT,
            user_id=10,
            user_role=UserRole.NODAL_OFFICER,
            objection_to_roles=[UserRole.COMMISSIONER],
            remarks="Nodal objections to Commissioner",
        )

        self.assertEqual(self.mock_app.objection_to_role, UserRole.COMMISSIONER)
        self.assertEqual(self.mock_app.status, ApplicationStatus.OBJECTED)
