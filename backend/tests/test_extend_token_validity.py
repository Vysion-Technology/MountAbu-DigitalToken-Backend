import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from backend.dao.application import ApplicationDAO
from backend.dbmodels.application import ApprovedApplicationPhase
from backend.meta import ApplicationPhaseStatus


class TestExtendTokenValidity(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_session = AsyncMock()
        self.dao = ApplicationDAO(self.mock_session)

    async def test_extend_validity_success(self):
        """Token expiring in 5 days should successfully extend by 30 days."""
        app_id = 1
        phase_num = 1
        user_id = 10

        # Phase activated 55 days ago (valid for 60 days, so 5 days left)
        activated_at = datetime.now() - timedelta(days=55)
        phase_rec = MagicMock(spec=ApprovedApplicationPhase)
        phase_rec.id = 101
        phase_rec.application_id = app_id
        phase_rec.phase = phase_num
        phase_rec.status = ApplicationPhaseStatus.ACTIVE
        phase_rec.activated_at = activated_at
        phase_rec.valid_till = None

        mock_res = MagicMock()
        mock_res.scalar_one_or_none = MagicMock(return_value=phase_rec)
        self.mock_session.execute = AsyncMock(return_value=mock_res)

        response = await self.dao.extend_token_validity(
            application_id=app_id,
            phase_num=phase_num,
            user_id=user_id,
            remarks="Contractor requested extension due to weather",
        )

        self.assertIn("successfully extended", response.message)
        self.assertIsNotNone(phase_rec.valid_till)
        # Expected new valid_till: (activated_at + 60 days) + 30 days = activated_at + 90 days
        expected_valid_till = activated_at + timedelta(days=60) + timedelta(days=30)
        self.assertEqual(
            phase_rec.valid_till.strftime("%Y-%m-%d %H:%M"),
            expected_valid_till.strftime("%Y-%m-%d %H:%M"),
        )
        self.mock_session.commit.assert_awaited_once()

    async def test_extend_validity_too_early(self):
        """Token expiring in 25 days cannot be extended (> 15 days)."""
        app_id = 1
        phase_num = 1
        user_id = 10

        # Activated 35 days ago (25 days left on a 60-day token)
        activated_at = datetime.now() - timedelta(days=35)
        phase_rec = MagicMock(spec=ApprovedApplicationPhase)
        phase_rec.id = 101
        phase_rec.application_id = app_id
        phase_rec.phase = phase_num
        phase_rec.status = ApplicationPhaseStatus.ACTIVE
        phase_rec.activated_at = activated_at
        phase_rec.valid_till = None

        mock_res = MagicMock()
        mock_res.scalar_one_or_none = MagicMock(return_value=phase_rec)
        self.mock_session.execute = AsyncMock(return_value=mock_res)

        with self.assertRaises(HTTPException) as ctx:
            await self.dao.extend_token_validity(app_id, phase_num, user_id)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("within the next 15 days", ctx.exception.detail)

    async def test_extend_validity_already_expired(self):
        """Token expired 2 days ago cannot be extended."""
        app_id = 1
        phase_num = 1
        user_id = 10

        # Activated 62 days ago
        activated_at = datetime.now() - timedelta(days=62)
        phase_rec = MagicMock(spec=ApprovedApplicationPhase)
        phase_rec.id = 101
        phase_rec.application_id = app_id
        phase_rec.phase = phase_num
        phase_rec.status = ApplicationPhaseStatus.ACTIVE
        phase_rec.activated_at = activated_at
        phase_rec.valid_till = None

        mock_res = MagicMock()
        mock_res.scalar_one_or_none = MagicMock(return_value=phase_rec)
        self.mock_session.execute = AsyncMock(return_value=mock_res)

        with self.assertRaises(HTTPException) as ctx:
            await self.dao.extend_token_validity(app_id, phase_num, user_id)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("already expired", ctx.exception.detail)

    async def test_extend_validity_not_active(self):
        """Token with WITHHELD status cannot be extended."""
        app_id = 1
        phase_num = 1
        user_id = 10

        phase_rec = MagicMock(spec=ApprovedApplicationPhase)
        phase_rec.id = 101
        phase_rec.application_id = app_id
        phase_rec.phase = phase_num
        phase_rec.status = ApplicationPhaseStatus.WITHHELD
        phase_rec.activated_at = datetime.now() - timedelta(days=55)
        phase_rec.valid_till = None

        mock_res = MagicMock()
        mock_res.scalar_one_or_none = MagicMock(return_value=phase_rec)
        self.mock_session.execute = AsyncMock(return_value=mock_res)

        with self.assertRaises(HTTPException) as ctx:
            await self.dao.extend_token_validity(app_id, phase_num, user_id)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Only ACTIVE tokens can be extended", ctx.exception.detail)
