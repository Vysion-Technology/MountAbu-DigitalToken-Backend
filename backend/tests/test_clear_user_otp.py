"""Tests for Superadmin Clear Mobile OTP & Purge Account features."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from backend.meta import UserRole
from backend.controllers.superadmin import (
    check_user_mobile,
    send_clear_otp,
    verify_and_delete_user,
    SendClearOTPRequest,
    VerifyClearOTPRequest,
)
from backend.schemas.base.auth import UserDetails


class TestSuperadminClearMobile(unittest.IsolatedAsyncioTestCase):
    """Tests for clear mobile inspection, OTP generation, and account purge."""

    async def asyncSetUp(self):
        self.mock_db = AsyncMock()
        self.superadmin_user = UserDetails(
            user_id=1,
            role=UserRole.SUPERADMIN,
            mobile="9999999999",
            name="Super Admin",
        )

    @patch("backend.controllers.superadmin.user_service.get_user_deletion_preview")
    async def test_check_mobile_success(self, mock_preview):
        mock_preview.return_value = {
            "user_id": 10,
            "name": "Accidental Citizen",
            "mobile": "9876543210",
            "role": "CITIZEN",
            "is_active": True,
            "created_at": "2026-01-01T10:00:00",
            "applications_count": 2,
            "complaints_count": 1,
            "tokens_count": 1,
            "schedules_count": 1,
            "has_active_data": True,
        }

        res = await check_user_mobile("9876543210", self.mock_db, self.superadmin_user)
        self.assertEqual(res.mobile, "9876543210")
        self.assertEqual(res.applications_count, 2)
        self.assertTrue(res.has_active_data)

    @patch("backend.controllers.superadmin.user_service.get_user_by_mobile")
    @patch("backend.controllers.superadmin.user_dao.get_otp_record")
    @patch("backend.controllers.superadmin.user_dao.get_valid_otp_record")
    @patch("backend.controllers.superadmin.user_dao.create_otp")
    @patch("backend.controllers.superadmin.sms_service.send_otp")
    async def test_send_clear_otp_success(self, mock_send_sms, mock_create_otp, mock_get_valid_otp, mock_get_otp, mock_get_user):
        mock_user = MagicMock()
        mock_user.id = 10
        mock_user.mobile = "9876543210"
        mock_get_user.return_value = mock_user

        mock_get_otp.return_value = None
        mock_get_valid_otp.return_value = None
        mock_send_sms.return_value = True

        req = SendClearOTPRequest(mobile="9876543210")
        res = await send_clear_otp(req, self.mock_db, self.superadmin_user)
        self.assertIn("OTP sent successfully", res.message)
        mock_create_otp.assert_awaited_once()
        mock_send_sms.assert_awaited_once()

    @patch("backend.controllers.superadmin.user_dao.get_otp_record")
    @patch("backend.controllers.superadmin.user_service.purge_and_delete_user")
    async def test_verify_and_delete_user_success(self, mock_purge, mock_get_otp):
        mock_otp = MagicMock()
        mock_otp.otp = "123456"
        mock_otp.valid_till = datetime.now() + timedelta(minutes=5)
        mock_get_otp.return_value = mock_otp

        mock_purge.return_value = True

        req = VerifyClearOTPRequest(mobile="9876543210", otp="123456")
        res = await verify_and_delete_user(req, self.mock_db, self.superadmin_user)
        self.assertIn("deleted successfully", res.message)
        mock_purge.assert_awaited_once_with(self.mock_db, "9876543210")


if __name__ == "__main__":
    unittest.main()
