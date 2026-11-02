import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, time
import zoneinfo
from backend.tasks.weekly_alerts import get_next_weekly_alert_time, run_weekly_alerts_job
from backend.services.sms import sms_service
from backend.meta import UserRole

IST = zoneinfo.ZoneInfo("Asia/Kolkata")

class TestWeeklyAlertsScheduler(unittest.IsolatedAsyncioTestCase):
    def test_next_alert_time_from_monday(self):
        # Monday 2026-10-12 09:00 IST -> Should be Tuesday 2026-10-13 10:00 IST
        monday_dt = datetime(2026, 10, 12, 9, 0, tzinfo=IST)
        next_dt = get_next_weekly_alert_time(monday_dt)
        self.assertEqual(next_dt.weekday(), 1)  # Tuesday
        self.assertEqual(next_dt.day, 13)
        self.assertEqual(next_dt.hour, 10)
        self.assertEqual(next_dt.minute, 0)

    def test_next_alert_time_from_tuesday_morning_before_10(self):
        # Tuesday 2026-10-13 08:30 IST -> Should be Tuesday 2026-10-13 10:00 IST
        tuesday_dt = datetime(2026, 10, 13, 8, 30, tzinfo=IST)
        next_dt = get_next_weekly_alert_time(tuesday_dt)
        self.assertEqual(next_dt.weekday(), 1)  # Same Tuesday
        self.assertEqual(next_dt.day, 13)
        self.assertEqual(next_dt.hour, 10)

    def test_next_alert_time_from_tuesday_after_10(self):
        # Tuesday 2026-10-13 11:00 IST -> Should be Thursday 2026-10-15 10:00 IST
        tuesday_dt = datetime(2026, 10, 13, 11, 0, tzinfo=IST)
        next_dt = get_next_weekly_alert_time(tuesday_dt)
        self.assertEqual(next_dt.weekday(), 3)  # Thursday
        self.assertEqual(next_dt.day, 15)
        self.assertEqual(next_dt.hour, 10)

    def test_next_alert_time_from_thursday_after_10(self):
        # Thursday 2026-10-15 12:00 IST -> Should be next Tuesday 2026-10-20 10:00 IST
        thursday_dt = datetime(2026, 10, 15, 12, 0, tzinfo=IST)
        next_dt = get_next_weekly_alert_time(thursday_dt)
        self.assertEqual(next_dt.weekday(), 1)  # Tuesday
        self.assertEqual(next_dt.day, 20)
        self.assertEqual(next_dt.hour, 10)

    async def test_send_weekly_alert_sms_execution(self):
        with patch.object(sms_service, "_send_flow_sms", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await sms_service.send_weekly_alert_sms(
                mobile="9876543210",
                name="Officer John",
                pending=4,
                objected=2,
                over15days=1,
            )
            self.assertTrue(result)
            mock_send.assert_awaited_once()
            call_payload = mock_send.call_args[0][0]
            self.assertEqual(call_payload["template_id"], sms_service.WEEKLY_ALERTS_TEMPLATE_ID)
            self.assertEqual(call_payload["recipients"][0]["mobiles"], "919876543210")
            self.assertEqual(call_payload["recipients"][0]["name"], "Officer John")
            self.assertEqual(call_payload["recipients"][0]["pending"], "4")
            self.assertEqual(call_payload["recipients"][0]["objected"], "2")
            self.assertEqual(call_payload["recipients"][0]["over15days"], "1")

    async def test_run_weekly_alerts_job_dispatches_sms(self):
        fake_user = MagicMock()
        fake_user.is_active = True
        fake_user.name = "JEN Official"
        fake_user.mobile = "9876543210"
        fake_user.role = UserRole.JEN

        fake_stats = {"pending": 3, "objected": 1, "over15days": 0}

        with patch("backend.tasks.weekly_alerts.AsyncSessionLocal") as mock_session_cls, \
             patch("backend.tasks.weekly_alerts.UserDAO") as mock_user_dao_cls, \
             patch("backend.tasks.weekly_alerts.ApplicationDAO") as mock_app_dao_cls, \
             patch("backend.tasks.weekly_alerts.sms_service.send_weekly_alert_sms", new_callable=AsyncMock) as mock_send_sms:
            
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            
            mock_user_dao = MagicMock()
            mock_user_dao.get_users_filtered = AsyncMock(return_value=[fake_user])
            mock_user_dao_cls.return_value = mock_user_dao

            mock_app_dao = MagicMock()
            mock_app_dao.get_authority_pending_stats = AsyncMock(return_value=fake_stats)
            mock_app_dao_cls.return_value = mock_app_dao

            mock_send_sms.return_value = True

            sent_count = await run_weekly_alerts_job()
            self.assertEqual(sent_count, 1)
            mock_send_sms.assert_awaited_once_with(
                mobile="9876543210",
                name="JEN Official",
                pending=3,
                objected=1,
                over15days=0,
            )

    async def test_send_vehicle_schedule_sms(self):
        with patch.object(sms_service, "_send_flow_sms", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await sms_service.send_vehicle_schedule_sms(
                mobile="9876543210",
                schedule_date="05 Nov 2026",
                slot_start="08:00 AM",
                slot_end="10:00 AM",
            )
            self.assertTrue(result)
            mock_send.assert_awaited_once()
            call_payload = mock_send.call_args[0][0]
            self.assertEqual(call_payload["template_id"], "1077214200045797362")
            self.assertEqual(call_payload["recipients"][0]["mobiles"], "919876543210")
            self.assertEqual(call_payload["recipients"][0]["var1"], "05 Nov 2026")
            self.assertEqual(call_payload["recipients"][0]["var2"], "08:00 AM")
            self.assertEqual(call_payload["recipients"][0]["var3"], "10:00 AM")

    async def test_send_schedule_cancellation_sms(self):
        with patch.object(sms_service, "_send_flow_sms", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await sms_service.send_schedule_cancellation_sms(
                mobile="9876543210",
                vehicle_number="RJ 27 GA 1234",
                token_no="TKN-2026-001",
                schedule_date="05 Nov 2026",
            )
            self.assertTrue(result)
            mock_send.assert_awaited_once()
            call_payload = mock_send.call_args[0][0]
            self.assertEqual(call_payload["template_id"], "1077487400034651029")
            self.assertEqual(call_payload["recipients"][0]["mobiles"], "919876543210")
            self.assertEqual(call_payload["recipients"][0]["var1"], "RJ 27 GA 1234")
            self.assertEqual(call_payload["recipients"][0]["var2"], "TKN-2026-001")
            self.assertEqual(call_payload["recipients"][0]["var3"], "05 Nov 2026")

if __name__ == "__main__":
    unittest.main()
