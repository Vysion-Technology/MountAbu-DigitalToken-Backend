import unittest
from datetime import datetime, time
import zoneinfo
from backend.tasks.weekly_alerts import get_next_weekly_alert_time

IST = zoneinfo.ZoneInfo("Asia/Kolkata")

class TestWeeklyAlertsScheduler(unittest.TestCase):
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

if __name__ == "__main__":
    unittest.main()
