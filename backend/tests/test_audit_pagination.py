import unittest
from unittest.mock import AsyncMock, MagicMock
from backend.controllers.audit import get_audit_logs


class TestAuditPagination(unittest.IsolatedAsyncioTestCase):
    async def test_get_audit_logs_offset_and_skip(self):
        """Verify get_audit_logs accepts both skip and offset parameters correctly."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_service = AsyncMock()
        mock_service.get_logs.return_value = ([], 0)

        from backend.controllers import audit
        original_service = audit.audit_service
        audit.audit_service = mock_service

        try:
            # Case 1: Client passes offset=20
            await get_audit_logs(
                skip=0,
                offset=20,
                limit=10,
                user_id=None,
                action=None,
                entity_type=None,
                start_date=None,
                end_date=None,
                db=mock_db,
                current_user=mock_user,
            )
            mock_service.get_logs.assert_called_with(
                mock_db, 20, 10, None, None, None, None, None
            )

            # Case 2: Client passes skip=30, offset=None
            mock_service.get_logs.reset_mock()
            await get_audit_logs(
                skip=30,
                offset=None,
                limit=10,
                user_id=None,
                action=None,
                entity_type=None,
                start_date=None,
                end_date=None,
                db=mock_db,
                current_user=mock_user,
            )
            mock_service.get_logs.assert_called_with(
                mock_db, 30, 10, None, None, None, None, None
            )
        finally:
            audit.audit_service = original_service

    async def test_audit_service_enrichment(self):
        """Verify audit service enriches logs with user name, role, and record_id."""
        from backend.services.audit import AuditService
        from backend.meta.audit import AuditAction
        from backend.meta import UserRole
        from datetime import datetime

        service = AuditService()
        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.entity_type = "APPLICATION"
        mock_log.action = AuditAction.CREATED
        mock_log.user_id = 42
        mock_log.previous_state = None
        mock_log.new_state = {"id": 105, "status": "SUBMITTED"}
        mock_log.created_at = datetime.now()

        service.dao = AsyncMock()
        service.dao.get_all.return_value = [mock_log]
        service.dao.count.return_value = 1

        mock_user = MagicMock()
        mock_user.id = 42
        mock_user.name = "Nodal Officer User"
        mock_user.role = UserRole.NODAL_OFFICER

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.execute.return_value = mock_result

        enriched, total = await service.get_logs(mock_session)

        self.assertEqual(total, 1)
        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0].user_name, "Nodal Officer User")
        self.assertEqual(enriched[0].user_role, "NODAL_OFFICER")
        self.assertEqual(enriched[0].record_id, 105)
