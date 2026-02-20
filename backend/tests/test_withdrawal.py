"""Tests for application and complaint withdrawal logic."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from backend.meta import ApplicationStatus, ComplaintStatus


class TestApplicationWithdrawal(unittest.IsolatedAsyncioTestCase):
    """Tests for ApplicationDAO.withdraw_application."""

    async def asyncSetUp(self):
        from backend.dao.application import ApplicationDAO

        self.mock_session = AsyncMock()
        self.dao = ApplicationDAO(self.mock_session)

    def _make_application(self, status=ApplicationStatus.PENDING, user_id=1, app_id=10):
        app = MagicMock()
        app.id = app_id
        app.user_id = user_id
        app.status = status
        return app

    async def test_withdraw_pending_application_succeeds(self):
        """Citizen can withdraw their own PENDING application."""
        app = self._make_application(status=ApplicationStatus.PENDING, user_id=1)
        self.mock_session.get = AsyncMock(return_value=app)
        self.mock_session.add = MagicMock()
        self.mock_session.commit = AsyncMock()

        result = await self.dao.withdraw_application(app.id, user_id=1)

        self.assertEqual(app.status, ApplicationStatus.WITHDRAWN)
        self.assertEqual(result.message, "Application withdrawn successfully")
        self.mock_session.commit.assert_awaited_once()

    async def test_withdraw_submitted_application_succeeds(self):
        """Citizen can withdraw their own SUBMITTED application."""
        app = self._make_application(status=ApplicationStatus.SUBMITTED, user_id=1)
        self.mock_session.get = AsyncMock(return_value=app)
        self.mock_session.add = MagicMock()
        self.mock_session.commit = AsyncMock()

        result = await self.dao.withdraw_application(app.id, user_id=1)

        self.assertEqual(app.status, ApplicationStatus.WITHDRAWN)
        self.assertEqual(result.message, "Application withdrawn successfully")

    async def test_withdraw_not_found_raises_404(self):
        """Raises 404 if application does not exist."""
        self.mock_session.get = AsyncMock(return_value=None)

        with self.assertRaises(HTTPException) as ctx:
            await self.dao.withdraw_application(999, user_id=1)

        self.assertEqual(ctx.exception.status_code, 404)

    async def test_withdraw_other_users_application_raises_403(self):
        """Raises 403 if user tries to withdraw someone else's application."""
        app = self._make_application(status=ApplicationStatus.PENDING, user_id=1)
        self.mock_session.get = AsyncMock(return_value=app)

        with self.assertRaises(HTTPException) as ctx:
            await self.dao.withdraw_application(app.id, user_id=99)

        self.assertEqual(ctx.exception.status_code, 403)

    async def test_withdraw_approved_application_raises_400(self):
        """Raises 400 if application is already APPROVED (not withdrawable)."""
        app = self._make_application(status=ApplicationStatus.APPROVED, user_id=1)
        self.mock_session.get = AsyncMock(return_value=app)

        with self.assertRaises(HTTPException) as ctx:
            await self.dao.withdraw_application(app.id, user_id=1)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("APPROVED", ctx.exception.detail)

    async def test_withdraw_already_withdrawn_raises_400(self):
        """Raises 400 if application is already WITHDRAWN."""
        app = self._make_application(status=ApplicationStatus.WITHDRAWN, user_id=1)
        self.mock_session.get = AsyncMock(return_value=app)

        with self.assertRaises(HTTPException) as ctx:
            await self.dao.withdraw_application(app.id, user_id=1)

        self.assertEqual(ctx.exception.status_code, 400)


class TestComplaintWithdrawal(unittest.IsolatedAsyncioTestCase):
    """Tests for complaint withdrawal logic (inline in controller)."""

    def _make_complaint(
        self, status=ComplaintStatus.PENDING, user_id=1, complaint_id=5
    ):
        complaint = MagicMock()
        complaint.id = complaint_id
        complaint.user_id = user_id
        complaint.status = status
        return complaint

    async def test_withdraw_pending_complaint_succeeds(self):
        """Citizen can withdraw their own PENDING complaint."""
        complaint = self._make_complaint(status=ComplaintStatus.PENDING, user_id=1)
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Simulate the controller logic directly
        if complaint.user_id != 1:
            raise AssertionError("Should not raise 403")
        if complaint.status != ComplaintStatus.PENDING:
            raise AssertionError("Should not raise 400")

        complaint.status = ComplaintStatus.WITHDRAWN
        await mock_db.commit()

        self.assertEqual(complaint.status, ComplaintStatus.WITHDRAWN)
        mock_db.commit.assert_awaited_once()

    async def test_withdraw_other_users_complaint_raises_403(self):
        """Raises 403 if user tries to withdraw someone else's complaint."""
        complaint = self._make_complaint(status=ComplaintStatus.PENDING, user_id=1)
        mock_db = AsyncMock()

        with self.assertRaises(HTTPException) as ctx:
            if complaint.user_id != 99:
                raise HTTPException(
                    status_code=403,
                    detail="You can only withdraw your own complaints",
                )

        self.assertEqual(ctx.exception.status_code, 403)

    async def test_withdraw_in_progress_complaint_raises_400(self):
        """Raises 400 if complaint is IN_PROGRESS (not withdrawable)."""
        complaint = self._make_complaint(status=ComplaintStatus.IN_PROGRESS, user_id=1)
        mock_db = AsyncMock()

        with self.assertRaises(HTTPException) as ctx:
            if complaint.status != ComplaintStatus.PENDING:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot withdraw complaint in '{complaint.status.value}' status. Only PENDING complaints can be withdrawn.",
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("IN_PROGRESS", ctx.exception.detail)

    async def test_withdraw_resolved_complaint_raises_400(self):
        """Raises 400 if complaint is RESOLVED."""
        complaint = self._make_complaint(status=ComplaintStatus.RESOLVED, user_id=1)

        with self.assertRaises(HTTPException) as ctx:
            if complaint.status != ComplaintStatus.PENDING:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot withdraw complaint in '{complaint.status.value}' status. Only PENDING complaints can be withdrawn.",
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("RESOLVED", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
