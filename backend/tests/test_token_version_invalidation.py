"""Tests for automatic token_version invalidation upon user credential / status changes."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from backend.meta import UserRole, JurisdictionZone
from backend.services.user import UserService
from backend.middlewares.auth import get_current_user, get_optional_user, get_current_user_id


class TestTokenVersionInvalidation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.service = UserService()
        self.mock_session = AsyncMock()
        self.mock_session.add = MagicMock()

    def _create_mock_user(
        self,
        user_id: int = 10,
        name: str = "Test User",
        mobile: str = "9876543210",
        username: str = "testuser",
        is_active: bool = True,
        token_version: int = 1,
        role: UserRole = UserRole.NODAL_OFFICER,
        jurisdiction_zone: JurisdictionZone = JurisdictionZone.ULB,
    ):
        user = MagicMock()
        user.id = user_id
        user.name = name
        user.mobile = mobile
        user.username = username
        user.is_active = is_active
        user.token_version = token_version
        user.role = role
        user.jurisdiction_zone = jurisdiction_zone
        user.password = "old_hashed_password"
        return user

    async def test_change_password_increments_token_version(self):
        """Changing password must increment token_version and commit."""
        user = self._create_mock_user(token_version=1)
        self.service.user_dao.get_by_id = AsyncMock(return_value=user)

        success = await self.service.change_password(self.mock_session, user.id, "new_secret_pass")

        self.assertTrue(success)
        self.assertEqual(user.token_version, 2)
        self.mock_session.add.assert_called_with(user)
        self.mock_session.commit.assert_awaited_once()

    async def test_update_user_mobile_increments_token_version(self):
        """Updating mobile must increment token_version to invalidate former holder's session."""
        user = self._create_mock_user(mobile="9876543210", token_version=1)
        self.service.user_dao.get_by_id = AsyncMock(return_value=user)

        updated_user = await self.service.update_user(
            self.mock_session,
            user_id=user.id,
            mobile="9123456780",
        )

        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.mobile, "9123456780")
        self.assertEqual(updated_user.token_version, 2)
        self.mock_session.add.assert_called_with(user)

    async def test_update_user_username_increments_token_version(self):
        """Updating username must increment token_version."""
        user = self._create_mock_user(username="oldname", token_version=3)
        self.service.user_dao.get_by_id = AsyncMock(return_value=user)

        updated_user = await self.service.update_user(
            self.mock_session,
            user_id=user.id,
            username="newname",
        )

        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.username, "newname")
        self.assertEqual(updated_user.token_version, 4)

    async def test_update_user_deactivation_increments_token_version(self):
        """Deactivating user (is_active=False) must increment token_version."""
        user = self._create_mock_user(is_active=True, token_version=2)
        self.service.user_dao.get_by_id = AsyncMock(return_value=user)

        updated_user = await self.service.update_user(
            self.mock_session,
            user_id=user.id,
            is_active=False,
        )

        self.assertIsNotNone(updated_user)
        self.assertFalse(updated_user.is_active)
        self.assertEqual(updated_user.token_version, 3)

    async def test_update_user_jurisdiction_increments_token_version(self):
        """Changing jurisdiction zone must increment token_version."""
        user = self._create_mock_user(jurisdiction_zone=JurisdictionZone.ULB, token_version=1)
        self.service.user_dao.get_by_id = AsyncMock(return_value=user)

        updated_user = await self.service.update_user(
            self.mock_session,
            user_id=user.id,
            jurisdiction_zone=JurisdictionZone.UIT,
        )

        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.jurisdiction_zone, JurisdictionZone.UIT)
        self.assertEqual(updated_user.token_version, 2)

    async def test_update_user_no_changes_does_not_increment_token_version(self):
        """If same values are sent, token_version should not increment."""
        user = self._create_mock_user(mobile="9876543210", username="nodal", token_version=1)
        self.service.user_dao.get_by_id = AsyncMock(return_value=user)

        updated_user = await self.service.update_user(
            self.mock_session,
            user_id=user.id,
            mobile="9876543210",
            username="nodal",
        )

        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.token_version, 1)

    async def test_soft_delete_user_increments_token_version(self):
        """Soft deleting a user sets is_active=False and increments token_version."""
        user = self._create_mock_user(is_active=True, token_version=5)
        self.service.user_dao.get_by_id = AsyncMock(return_value=user)

        success = await self.service.delete_user(self.mock_session, user.id)

        self.assertTrue(success)
        self.assertFalse(user.is_active)
        self.assertEqual(user.token_version, 6)


class TestAuthMiddlewareValidation(unittest.IsolatedAsyncioTestCase):
    @patch("backend.middlewares.auth.jwt.decode")
    async def test_get_current_user_rejects_mismatched_token_version(self, mock_jwt_decode):
        """Middleware rejects requests where JWT version does not match DB token_version."""
        mock_jwt_decode.return_value = {"sub": "10", "role": "NODAL_OFFICER", "version": 1}
        mock_creds = MagicMock(credentials="test_jwt")

        mock_user = MagicMock(id=10, is_active=True, token_version=2)  # DB has version 2

        with patch("backend.dao.user.UserDAO.get_by_id", AsyncMock(return_value=mock_user)):
            with self.assertRaises(HTTPException) as ctx:
                await get_current_user(mock_creds)

            self.assertEqual(ctx.exception.status_code, 401)

    @patch("backend.middlewares.auth.jwt.decode")
    async def test_get_current_user_rejects_inactive_user(self, mock_jwt_decode):
        """Middleware rejects requests from inactive users even if token_version matches."""
        mock_jwt_decode.return_value = {"sub": "10", "role": "NODAL_OFFICER", "version": 1}
        mock_creds = MagicMock(credentials="test_jwt")

        mock_user = MagicMock(id=10, is_active=False, token_version=1)  # is_active=False

        with patch("backend.dao.user.UserDAO.get_by_id", AsyncMock(return_value=mock_user)):
            with self.assertRaises(HTTPException) as ctx:
                await get_current_user(mock_creds)

            self.assertEqual(ctx.exception.status_code, 401)

    @patch("backend.middlewares.auth.jwt.decode")
    async def test_get_current_user_accepts_valid_active_user(self, mock_jwt_decode):
        """Middleware accepts requests with valid token_version and active status."""
        mock_jwt_decode.return_value = {"sub": "10", "role": "NODAL_OFFICER", "version": 2}
        mock_creds = MagicMock(credentials="test_jwt")

        mock_user = MagicMock(id=10, is_active=True, token_version=2)

        with patch("backend.dao.user.UserDAO.get_by_id", AsyncMock(return_value=mock_user)):
            details = await get_current_user(mock_creds)
            self.assertEqual(details.user_id, 10)
            self.assertEqual(details.token_version, 2)
            self.assertEqual(details.role, UserRole.NODAL_OFFICER)

    async def test_get_current_user_id_delegates_to_current_user(self):
        """get_current_user_id returns user_id from the validated current_user."""
        mock_current_user = MagicMock(user_id=42)
        res = await get_current_user_id(mock_current_user)
        self.assertEqual(res, 42)
