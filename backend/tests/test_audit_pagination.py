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
