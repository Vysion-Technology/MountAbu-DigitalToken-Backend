import unittest
from backend.core.workflow import validate_transition
from backend.meta import ApplicationStatus, ApplicationType, UserRole, WorkflowAction

class TestNewTransitions(unittest.TestCase):
    def test_new_construction_approved_to_rejected(self):
        """NODAL_OFFICER/SUPERADMIN can reject a NEW construction application when APPROVED."""
        for role in [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN]:
            next_status = validate_transition(
                current_status=ApplicationStatus.APPROVED,
                action=WorkflowAction.REJECT,
                app_type=ApplicationType.NEW,
                user_role=role
            )
            self.assertEqual(next_status, ApplicationStatus.REJECTED)

    def test_new_construction_approved_to_objected(self):
        """NODAL_OFFICER/SUPERADMIN can object to a NEW construction application when APPROVED."""
        for role in [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN]:
            next_status = validate_transition(
                current_status=ApplicationStatus.APPROVED,
                action=WorkflowAction.OBJECT,
                app_type=ApplicationType.NEW,
                user_role=role
            )
            self.assertEqual(next_status, ApplicationStatus.OBJECTED)

    def test_new_construction_objected_to_objected(self):
        """NODAL_OFFICER/SUPERADMIN can object to a NEW construction application when already OBJECTED."""
        for role in [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN]:
            next_status = validate_transition(
                current_status=ApplicationStatus.OBJECTED,
                action=WorkflowAction.OBJECT,
                app_type=ApplicationType.NEW,
                user_role=role
            )
            self.assertEqual(next_status, ApplicationStatus.OBJECTED)

    def test_renovation_objected_to_objected(self):
        """COMMISSIONER/SUPERADMIN can object to a RENOVATION application when already OBJECTED."""
        for role in [UserRole.COMMISSIONER, UserRole.SUPERADMIN]:
            next_status = validate_transition(
                current_status=ApplicationStatus.OBJECTED,
                action=WorkflowAction.OBJECT,
                app_type=ApplicationType.RENOVATION,
                user_role=role
            )
            self.assertEqual(next_status, ApplicationStatus.OBJECTED)

    def test_unauthorized_role_raises_value_error(self):
        """An unauthorized role like CITIZEN cannot perform reject or object on APPROVED/OBJECTED applications."""
        with self.assertRaises(ValueError):
            validate_transition(
                current_status=ApplicationStatus.APPROVED,
                action=WorkflowAction.REJECT,
                app_type=ApplicationType.NEW,
                user_role=UserRole.CITIZEN
            )

        with self.assertRaises(ValueError):
            validate_transition(
                current_status=ApplicationStatus.OBJECTED,
                action=WorkflowAction.OBJECT,
                app_type=ApplicationType.RENOVATION,
                user_role=UserRole.CITIZEN
            )
