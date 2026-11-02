import unittest
from unittest.mock import AsyncMock, MagicMock
from backend.dao.notification import NotificationDAO
from backend.dbmodels.notification import Notification


class TestNotificationDAO(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_session = AsyncMock()
        self.dao = NotificationDAO(self.mock_session)

    async def test_create_and_get_notifications(self):
        # Mock creating notification
        notif = await self.dao.create_notification(
            user_id=1,
            title="Objection Response Received",
            message="Citizen responded to objection",
            application_id=10,
        )
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()

    async def test_mark_all_as_read(self):
        res_mock = MagicMock()
        res_mock.rowcount = 3
        self.mock_session.execute.return_value = res_mock

        count = await self.dao.mark_all_as_read(user_id=1)
        self.assertEqual(count, 3)
        self.mock_session.commit.assert_called_once()
