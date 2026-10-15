import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.meta import UserRole
from backend.services.authority_dashboard import AuthorityDashboardService
from backend.schemas.response.authority_dashboard import AuthorityDashboardResponse


class TestAuthorityPendency(unittest.IsolatedAsyncioTestCase):
    async def test_authority_pendency_visibility_and_nodal_exclusion(self):
        mock_dao = MagicMock()
        mock_dao.superadmin_kpis = AsyncMock(return_value=[])
        mock_dao.application_status_breakdown = AsyncMock(return_value=[])
        mock_dao.complaints_by_category = AsyncMock(return_value=[])
        mock_dao.ward_activity = AsyncMock(return_value=[])
        mock_dao.complaint_officer_kpis = AsyncMock(return_value=[])
        mock_dao.complaint_resolution_status = AsyncMock(return_value=[])
        mock_dao.complaint_list = AsyncMock(return_value=[])
        mock_dao.session = MagicMock()

        service = AuthorityDashboardService(mock_dao)

        fake_stats_all = [
            {"role": UserRole.NODAL_OFFICER.value, "name": "Nodal Officer", "pending_count": 5, "objected_count": 1, "over_15_days_count": 2, "total_count": 6},
            {"role": UserRole.COMMISSIONER.value, "name": "Commissioner", "pending_count": 3, "objected_count": 0, "over_15_days_count": 1, "total_count": 3},
            {"role": UserRole.JEN.value, "name": "Junior Engineer (JEN)", "pending_count": 10, "objected_count": 2, "over_15_days_count": 4, "total_count": 12},
        ]

        with patch("backend.services.authority_dashboard.ApplicationDAO") as mock_app_dao_cls:
            mock_app_dao = MagicMock()
            mock_app_dao.get_batch_authority_pending_stats = AsyncMock(return_value=fake_stats_all)
            mock_app_dao_cls.return_value = mock_app_dao

            # 1. Superadmin should get pendency stats, target_roles includes NODAL_OFFICER
            resp_sa = await service.get_dashboard(UserRole.SUPERADMIN, user_id=1)
            self.assertIsNotNone(resp_sa.authority_pendency)
            self.assertEqual(len(resp_sa.authority_pendency), 3)
            called_roles_sa = mock_app_dao.get_batch_authority_pending_stats.call_args[0][0]
            self.assertIn(UserRole.NODAL_OFFICER, called_roles_sa)
            self.assertIn(UserRole.COMMISSIONER, called_roles_sa)

            # 2. Commissioner: MUST NOT include NODAL_OFFICER in target_roles!
            mock_app_dao.get_batch_authority_pending_stats.reset_mock()
            mock_app_dao.get_batch_authority_pending_stats.return_value = [
                s for s in fake_stats_all if s["role"] != UserRole.NODAL_OFFICER.value
            ]

            resp_comm = await service.get_dashboard(UserRole.COMMISSIONER, user_id=2)
            self.assertIsNotNone(resp_comm.authority_pendency)
            called_roles_comm = mock_app_dao.get_batch_authority_pending_stats.call_args[0][0]
            self.assertNotIn(UserRole.NODAL_OFFICER, called_roles_comm)
            self.assertIn(UserRole.COMMISSIONER, called_roles_comm)
            self.assertTrue(all(item.role != UserRole.NODAL_OFFICER.value for item in resp_comm.authority_pendency))

            # 3. JEN should NOT get authority_pendency
            mock_dao.jen_kpis = AsyncMock(return_value=[])
            mock_dao.jen_verification_status = AsyncMock(return_value=[])
            mock_dao.jen_avg_verification_trend = AsyncMock(return_value=[])
            mock_dao.jen_latest_applications = AsyncMock(return_value=[])
            resp_jen = await service.get_dashboard(UserRole.JEN, user_id=3)
            self.assertIsNone(resp_jen.authority_pendency)
