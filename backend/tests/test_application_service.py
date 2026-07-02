import unittest
from unittest.mock import AsyncMock, MagicMock
from backend.services.application import ApplicationService
from backend.schemas.request.application import ApplicationCreate
from backend.schemas.response.application import ApplicationResponse
from backend.schemas.base.auth import UserDetails
from backend.meta import UserRole, ApplicationStatus, ApplicationType, PropertyUsageType, JurisdictionZone

class TestApplicationService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_dao = AsyncMock()
        self.service = ApplicationService(self.mock_dao)

    async def test_create_application(self):
        # Setup
        app_create = MagicMock(spec=ApplicationCreate)
        # Mocking properties accessed by the service or dao if any (though service just passes it)
        # However, to be safe against pydantic validation if instantiated:
        user_id = 1
        mobile = "1234567890"
        
        expected_response = ApplicationResponse(
            id=1, user_id=user_id, applicant_name="Test", 
            father_name="Father", mobile=mobile, email="test@test.com",
            current_address="Address", property_address="Prop Address",
            title="Title", work_description="Work", 
            contractor_name="Contractor",
            is_agriculture_land=False, property_usage=PropertyUsageType.DOMESTIC,
            department_id=1, ward_id=1, status=ApplicationStatus.PENDING, type=ApplicationType.NEW,
            num_stages=None, jurisdiction_zone=JurisdictionZone.ULB
        )
        self.mock_dao.create_application.return_value = expected_response

        # Execute
        result = await self.service.create_application(app_create, user_id, mobile)

        # Verify
        self.mock_dao.create_application.assert_called_once_with(app_create, user_id, mobile)
        self.assertEqual(result, expected_response)

    async def test_get_application_sanitation_naka_incharge(self):
        # Setup
        app_id = 1
        user = UserDetails(role=UserRole.NAKA_INCHARGE, user_id=2)
        
        # Use a MagicMock for response so we can modify attributes easily and simulate Pydantic model
        original_response = MagicMock(spec=ApplicationResponse)
        original_response.mobile = "1234567890"
        original_response.email = "test@test.com"
        original_response.current_address = "Real Address"
        
        self.mock_dao.get_application.return_value = original_response

        # Execute
        result = await self.service.get_application(app_id, user)

        # Verify
        self.assertEqual(result.mobile, "******")
        self.assertEqual(result.email, "******")
        self.assertEqual(result.current_address, "******")
        self.mock_dao.get_application.assert_called_once_with(app_id)

    async def test_get_application_no_sanitation_citizen(self):
        # Setup
        app_id = 1
        user = UserDetails(role=UserRole.CITIZEN, user_id=1)
        
        original_response = MagicMock(spec=ApplicationResponse)
        original_response.mobile = "1234567890"
        original_response.email = "test@test.com"
        original_response.current_address = "Real Address"
        
        self.mock_dao.get_application.return_value = original_response

        # Execute
        result = await self.service.get_application(app_id, user)

        # Verify
        self.assertEqual(result.mobile, "1234567890")
        self.assertEqual(result.email, "test@test.com")
        self.assertEqual(result.current_address, "Real Address")
        self.mock_dao.get_application.assert_called_once_with(app_id)

if __name__ == '__main__':
    unittest.main()
