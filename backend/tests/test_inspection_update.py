import unittest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from backend.meta import ApplicationStatus, ApplicationType
from backend.dao.application import ApplicationDAO

class TestInspectionUpdate(unittest.IsolatedAsyncioTestCase):
    """Tests for ApplicationDAO.update_inspection_report."""

    async def asyncSetUp(self):
        self.mock_session = AsyncMock()
        self.dao = ApplicationDAO(self.mock_session)

    def _make_application(self, app_type=ApplicationType.NEW, status=ApplicationStatus.APPROVED, app_id=1):
        app = MagicMock()
        app.id = app_id
        app.type = app_type
        app.status = status
        return app

    def _make_inspection(self, app_id=1, inspection_id=10):
        insp = MagicMock()
        insp.id = inspection_id
        insp.application_id = app_id
        insp.remarks = "Original remarks"
        insp.recommended_phases = 2
        return insp

    async def test_update_inspection_app_not_found(self):
        """Should raise 404 if application does not exist."""
        self.mock_session.get = AsyncMock(return_value=None)
        with self.assertRaises(HTTPException) as context:
            await self.dao.update_inspection_report(
                application_id=999,
                user_id=2,
                remarks="Test remarks"
            )
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.detail, "Application not found")

    async def test_update_inspection_invalid_status_new_construction(self):
        """New Construction update inspection should fail if status is not APPROVED or TOKEN_GENERATED."""
        app = self._make_application(app_type=ApplicationType.NEW, status=ApplicationStatus.SUBMITTED)
        self.mock_session.get = AsyncMock(return_value=app)
        
        with self.assertRaises(HTTPException) as context:
            await self.dao.update_inspection_report(
                application_id=app.id,
                user_id=2,
                remarks="Test remarks"
            )
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Inspection update is only allowed on APPROVED or TOKEN_GENERATED applications", context.exception.detail)

    async def test_update_inspection_invalid_status_renovation(self):
        """Renovation update inspection should fail if status is not FORWARDED, APPROVED, or TOKEN_GENERATED."""
        app = self._make_application(app_type=ApplicationType.RENOVATION, status=ApplicationStatus.SUBMITTED)
        self.mock_session.get = AsyncMock(return_value=app)
        
        with self.assertRaises(HTTPException) as context:
            await self.dao.update_inspection_report(
                application_id=app.id,
                user_id=2,
                remarks="Test remarks"
            )
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Inspection update is only allowed on FORWARDED, APPROVED, or TOKEN_GENERATED applications", context.exception.detail)

    async def test_update_inspection_report_not_found(self):
        """Should raise 404 if no existing inspection report is found."""
        app = self._make_application(app_type=ApplicationType.NEW, status=ApplicationStatus.APPROVED)
        self.mock_session.get = AsyncMock(return_value=app)
        
        # Mocking db execution return value for empty inspection report query
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        self.mock_session.execute = AsyncMock(return_value=mock_result)

        with self.assertRaises(HTTPException) as context:
            await self.dao.update_inspection_report(
                application_id=app.id,
                user_id=2,
                remarks="Test remarks"
            )
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.detail, "Inspection report not found")

    async def test_update_inspection_success(self):
        """Should successfully update existing inspection report attributes and commit."""
        app = self._make_application(app_type=ApplicationType.NEW, status=ApplicationStatus.APPROVED)
        self.mock_session.get = AsyncMock(return_value=app)
        
        inspection = self._make_inspection(app_id=app.id)
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = inspection
        self.mock_session.execute = AsyncMock(return_value=mock_result)
        self.mock_session.commit = AsyncMock()

        result = await self.dao.update_inspection_report(
            application_id=app.id,
            user_id=2,
            remarks="Updated remarks",
            recommended_phases=3,
            latitude=24.59,
            longitude=72.71,
            media_paths=["/path/to/img1.jpg"]
        )

        self.assertEqual(result.message, "Inspection report updated successfully")
        self.assertEqual(inspection.remarks, "Updated remarks")
        self.assertEqual(inspection.recommended_phases, 3)
        self.assertEqual(inspection.latitude, 24.59)
        self.assertEqual(inspection.longitude, 72.71)
        self.assertEqual(inspection.media_paths, ["/path/to/img1.jpg"])
        self.assertEqual(inspection.inspected_by, 2)
        self.mock_session.commit.assert_awaited_once()

    async def test_update_inspection_multiple_reports_updates_latest(self):
        """Should update the latest inspection report (ordered by ID descending) if multiple exist."""
        app = self._make_application(app_type=ApplicationType.NEW, status=ApplicationStatus.APPROVED)
        self.mock_session.get = AsyncMock(return_value=app)
        
        # We simulate order_by(InspectionReport.id.desc()) being called, so the first scalar is the newest
        latest_inspection = self._make_inspection(app_id=app.id, inspection_id=15)
        latest_inspection.remarks = "Old remarks"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = latest_inspection
        self.mock_session.execute = AsyncMock(return_value=mock_result)
        self.mock_session.commit = AsyncMock()

        await self.dao.update_inspection_report(
            application_id=app.id,
            user_id=3,
            remarks="New remarks"
        )

        self.assertEqual(latest_inspection.remarks, "New remarks")
        self.assertEqual(latest_inspection.inspected_by, 3)

    async def test_update_inspection_success_when_objected_to_jen(self):
        """Should allow updating inspection if the application is in OBJECTED status and objected to JEN."""
        app = self._make_application(app_type=ApplicationType.NEW, status=ApplicationStatus.OBJECTED)
        from backend.meta import UserRole
        app.objection_to_role = UserRole.JEN
        self.mock_session.get = AsyncMock(return_value=app)
        
        inspection = self._make_inspection(app_id=app.id)
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = inspection
        self.mock_session.execute = AsyncMock(return_value=mock_result)
        self.mock_session.commit = AsyncMock()

        result = await self.dao.update_inspection_report(
            application_id=app.id,
            user_id=2,
            remarks="Updated remarks when objected to JEN"
        )
        self.assertEqual(result.message, "Inspection report updated successfully")
        self.assertEqual(inspection.remarks, "Updated remarks when objected to JEN")

