import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from backend.controllers.application import create_application
from backend.schemas.request.application import ApplicationCreate

class TestAllowNewApplications(unittest.IsolatedAsyncioTestCase):
    @patch("backend.controllers.application.settings")
    async def test_create_application_suspended(self, mock_settings):
        # Setup setting to False (suspended)
        mock_settings.ALLOW_NEW_APPLICATIONS = False

        app_create = MagicMock(spec=ApplicationCreate)
        mock_app_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_db = AsyncMock()

        # Execute & Verify that it raises 503 HTTP Exception
        with self.assertRaises(HTTPException) as context:
            await create_application(
                application_create=app_create,
                application_service=mock_app_service,
                user_id=1,
                user_service=mock_user_service,
                db=mock_db
            )
        
        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("Due to some maintenance", context.exception.detail)
        # Ensure service was never called
        mock_app_service.create_application.assert_not_called()

    @patch("backend.controllers.application.settings")
    async def test_create_application_allowed(self, mock_settings):
        # Setup setting to True (allowed)
        mock_settings.ALLOW_NEW_APPLICATIONS = True

        app_create = MagicMock(spec=ApplicationCreate)
        mock_app_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_db = AsyncMock()

        # Setup user return
        mock_user = MagicMock()
        mock_user.mobile = "1234567890"
        mock_user_service.get_user_by_id.return_value = mock_user

        # Setup service return
        mock_response = MagicMock()
        mock_app_service.create_application.return_value = mock_response

        # Execute
        await create_application(
            application_create=app_create,
            application_service=mock_app_service,
            user_id=1,
            user_service=mock_user_service,
            db=mock_db
        )

        # Verify service was called
        mock_app_service.create_application.assert_called_once()
