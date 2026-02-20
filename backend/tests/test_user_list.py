"""Tests for UserDAO.get_users_filtered (user listing API)."""

import unittest
from unittest.mock import AsyncMock, MagicMock

from backend.meta import UserRole


def _make_user(role: UserRole, user_id: int, name: str = "Test"):
    user = MagicMock()
    user.id = user_id
    user.role = role
    user.name = name
    return user


class TestUserListFiltering(unittest.IsolatedAsyncioTestCase):
    """Tests for UserDAO.get_users_filtered."""

    async def asyncSetUp(self):
        from backend.dao.user import UserDAO

        self.dao = UserDAO()
        self.mock_session = AsyncMock()

    async def _mock_query_result(self, users):
        """Helper: make session.execute return a mock that yields the given users."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = users
        self.mock_session.execute = AsyncMock(return_value=mock_result)

    async def test_get_citizens_returns_only_citizens(self):
        """is_citizen=True should return only CITIZEN-role users."""
        citizens = [
            _make_user(UserRole.CITIZEN, 1, "Alice"),
            _make_user(UserRole.CITIZEN, 2, "Bob"),
        ]
        await self._mock_query_result(citizens)

        result = await self.dao.get_users_filtered(self.mock_session, is_citizen=True)

        self.assertEqual(len(result), 2)
        for user in result:
            self.assertEqual(user.role, UserRole.CITIZEN)

    async def test_get_officials_returns_no_citizens(self):
        """is_citizen=False should return only non-CITIZEN users."""
        officials = [
            _make_user(UserRole.NODAL_OFFICER, 3, "Charlie"),
            _make_user(UserRole.COMMISSIONER, 4, "Diana"),
            _make_user(UserRole.SUPERADMIN, 5, "Eve"),
        ]
        await self._mock_query_result(officials)

        result = await self.dao.get_users_filtered(self.mock_session, is_citizen=False)

        self.assertEqual(len(result), 3)
        for user in result:
            self.assertNotEqual(user.role, UserRole.CITIZEN)

    async def test_get_citizens_empty_list(self):
        """Returns empty list when no citizens exist."""
        await self._mock_query_result([])

        result = await self.dao.get_users_filtered(self.mock_session, is_citizen=True)

        self.assertEqual(result, [])

    async def test_get_officials_empty_list(self):
        """Returns empty list when no officials exist."""
        await self._mock_query_result([])

        result = await self.dao.get_users_filtered(self.mock_session, is_citizen=False)

        self.assertEqual(result, [])

    async def test_citizen_filter_queries_db(self):
        """Verifies that session.execute is called when filtering citizens."""
        await self._mock_query_result([])

        await self.dao.get_users_filtered(self.mock_session, is_citizen=True)

        self.mock_session.execute.assert_awaited_once()

    async def test_official_filter_queries_db(self):
        """Verifies that session.execute is called when filtering officials."""
        await self._mock_query_result([])

        await self.dao.get_users_filtered(self.mock_session, is_citizen=False)

        self.mock_session.execute.assert_awaited_once()

    async def test_mixed_roles_in_officials(self):
        """Officials list can contain multiple non-citizen roles."""
        officials = [
            _make_user(UserRole.NODAL_OFFICER, 10),
            _make_user(UserRole.COMMISSIONER, 11),
            _make_user(UserRole.SUPERADMIN, 12),
            _make_user(UserRole.JEN, 13),
            _make_user(UserRole.NAKA_INCHARGE, 14),
        ]
        await self._mock_query_result(officials)

        result = await self.dao.get_users_filtered(self.mock_session, is_citizen=False)

        roles = {u.role for u in result}
        self.assertNotIn(UserRole.CITIZEN, roles)
        self.assertEqual(len(result), 5)


if __name__ == "__main__":
    unittest.main()
