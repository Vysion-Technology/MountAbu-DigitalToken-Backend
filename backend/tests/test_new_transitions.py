import unittest
from backend.core.workflow import validate_transition
from backend.meta import ApplicationStatus, ApplicationType, UserRole, WorkflowAction, PropertyUsageType, JurisdictionZone

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

    def test_rejection_remarks_serialization(self):
        """ApplicationResponse should extract the latest REJECT action remarks."""
        from backend.schemas.response.application import ApplicationResponse
        from datetime import datetime, timedelta

        # Mocking application data as a dictionary
        app_data = {
            "id": 1,
            "user_id": 10,
            "applicant_name": "John Doe",
            "father_name": "Sr Doe",
            "mobile": "1234567890",
            "email": "john@doe.com",
            "current_address": "Addr 1",
            "property_address": "Addr 2",
            "title": "Renovation Title",
            "work_description": "Paint",
            "contractor_name": None,
            "department_id": None,
            "ward_id": None,
            "is_agriculture_land": False,
            "property_usage": PropertyUsageType.DOMESTIC,
            "jurisdiction_zone": JurisdictionZone.ULB,
            "status": ApplicationStatus.REJECTED,
            "type": ApplicationType.RENOVATION,
            "num_stages": 3,
            "action_logs": [
                {
                    "action": WorkflowAction.OBJECT,
                    "remarks": "Missing documents",
                    "performed_at": datetime.now() - timedelta(hours=2)
                },
                {
                    "action": WorkflowAction.REJECT,
                    "remarks": "Fake documents, rejected",
                    "performed_at": datetime.now() - timedelta(hours=1)
                },
                {
                    "action": WorkflowAction.APPROVE,
                    "remarks": "Not a reject action",
                    "performed_at": datetime.now()
                }
            ]
        }

        response = ApplicationResponse.model_validate(app_data)
        self.assertEqual(response.rejection_remarks, "Fake documents, rejected")
