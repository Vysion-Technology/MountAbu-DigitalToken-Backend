"""Blacklist service - handles automatic and manual blacklisting."""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import (
    User,
    UserBlacklistStatus,
    ApplicationRejection,
    AuditLog,
)
from app.services.sms_service import send_notification_sms

logger = logging.getLogger(__name__)


class BlacklistService:
    """Service for managing user blacklist status."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.threshold = settings.BLACKLIST_REJECTION_THRESHOLD  # Default: 3

    async def check_blacklist(self, user_id: UUID) -> Tuple[bool, Optional[str]]:
        """
        Check if user is blacklisted.
        Returns (is_blacklisted, reason).
        """
        result = await self.db.execute(
            select(UserBlacklistStatus).where(UserBlacklistStatus.user_id == user_id)
        )
        status = result.scalar_one_or_none()

        if not status:
            return False, None

        if status.is_blacklisted:
            return (
                True,
                status.blacklist_reason
                or "User is blacklisted due to repeated rejections.",
            )

        return False, None

    async def process_rejection(
        self,
        user_id: UUID,
        application_id: UUID,
        rejected_by: UUID,
        rejected_by_role: str,
        reason: str,
        category: str,
        comments: Optional[str] = None,
    ) -> dict:
        """
        Process application rejection and update blacklist status.
        Automatically blacklists after 3 consecutive rejections.
        """
        # Get or create blacklist status
        result = await self.db.execute(
            select(UserBlacklistStatus).where(UserBlacklistStatus.user_id == user_id)
        )
        status = result.scalar_one_or_none()

        if not status:
            status = UserBlacklistStatus(
                user_id=user_id,
                consecutive_rejections=0,
                total_rejections=0,
                total_approvals=0,
            )
            self.db.add(status)

        # Increment counters
        status.consecutive_rejections += 1
        status.total_rejections += 1
        status.last_rejection_at = datetime.now(timezone.utc)
        status.last_rejection_application_id = application_id

        # Record rejection
        rejection = ApplicationRejection(
            user_id=user_id,
            application_id=application_id,
            rejected_by=rejected_by,
            rejected_by_role=rejected_by_role,
            rejection_reason=reason,
            rejection_category=category,
            authority_comments=comments,
            was_consecutive=True,
            consecutive_count=status.consecutive_rejections,
        )
        self.db.add(rejection)

        # Check if blacklist threshold reached
        triggered_blacklist = False
        if status.consecutive_rejections >= self.threshold:
            triggered_blacklist = True
            await self._apply_blacklist(
                status=status,
                reason=f"Automatic blacklist: {self.threshold} consecutive rejected applications",
                category="AUTO_CONSECUTIVE",
            )
            rejection.triggered_blacklist = True

        # Issue warning at threshold - 1
        elif status.consecutive_rejections == self.threshold - 1:
            status.warning_issued = True
            status.warning_issued_at = datetime.now(timezone.utc)
            await self._send_warning(user_id)

        await self.db.flush()

        return {
            "consecutive_rejections": status.consecutive_rejections,
            "is_blacklisted": status.is_blacklisted,
            "warning_issued": status.warning_issued,
            "triggered_blacklist": triggered_blacklist,
        }

    async def _apply_blacklist(
        self,
        status: UserBlacklistStatus,
        reason: str,
        category: str,
        blacklisted_by: Optional[UUID] = None,
    ):
        """Apply blacklist to user."""
        status.is_blacklisted = True
        status.blacklisted_at = datetime.now(timezone.utc)
        status.blacklist_reason = reason
        status.blacklist_category = category
        status.blacklisted_by = blacklisted_by

        # Create audit log
        audit = AuditLog(
            user_id=status.user_id,
            action="AUTO_BLACKLIST" if not blacklisted_by else "MANUAL_BLACKLIST",
            resource_type="USER",
            resource_id=status.user_id,
            description=reason,
            new_values={
                "is_blacklisted": True,
                "consecutive_rejections": status.consecutive_rejections,
                "category": category,
            },
        )
        self.db.add(audit)

        # Send notification to user
        await self._send_blacklist_notification(status.user_id, reason)

        logger.warning(f"User {status.user_id} has been blacklisted: {reason}")

    async def _send_warning(self, user_id: UUID):
        """Send warning notification to user."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user and user.mobile:
            message = (
                f"Warning: You have {self.threshold - 1} consecutive rejected applications. "
                f"One more rejection will result in automatic blacklisting."
            )
            await send_notification_sms(user.mobile, message)

        logger.info(f"Warning issued to user {user_id}")

    async def _send_blacklist_notification(self, user_id: UUID, reason: str):
        """Send blacklist notification to user."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user and user.mobile:
            message = (
                "Your account has been blacklisted due to repeated rejected applications. "
                "Please visit the SDM office for resolution."
            )
            await send_notification_sms(user.mobile, message)

    async def reset_on_approval(self, user_id: UUID):
        """Reset consecutive rejections on approval."""
        result = await self.db.execute(
            select(UserBlacklistStatus).where(UserBlacklistStatus.user_id == user_id)
        )
        status = result.scalar_one_or_none()

        if status:
            status.consecutive_rejections = 0
            status.total_approvals += 1
            status.warning_issued = False

            logger.info(f"Reset consecutive rejections for user {user_id}")

    async def whitelist_user(
        self,
        user_id: UUID,
        whitelisted_by: UUID,
        reason: str,
        conditions: Optional[List[str]] = None,
    ) -> dict:
        """Whitelist a blacklisted user."""
        result = await self.db.execute(
            select(UserBlacklistStatus)
            .options(selectinload(UserBlacklistStatus.user))
            .where(UserBlacklistStatus.user_id == user_id)
        )
        status = result.scalar_one_or_none()

        if not status:
            raise ValueError("User blacklist status not found")

        if not status.is_blacklisted:
            raise ValueError("User is not blacklisted")

        # Update status
        previous_state = {
            "is_blacklisted": True,
            "blacklisted_at": status.blacklisted_at.isoformat()
            if status.blacklisted_at
            else None,
        }

        status.is_blacklisted = False
        status.whitelisted_at = datetime.now(timezone.utc)
        status.whitelisted_by = whitelisted_by
        status.whitelist_reason = reason
        status.consecutive_rejections = 0  # Reset counter
        status.warning_issued = False

        # Create audit log
        audit = AuditLog(
            user_id=whitelisted_by,
            action="WHITELIST",
            resource_type="USER",
            resource_id=user_id,
            description=f"User whitelisted: {reason}",
            old_values=previous_state,
            new_values={
                "is_blacklisted": False,
                "reason": reason,
                "conditions": conditions,
            },
        )
        self.db.add(audit)

        # Send notification
        if status.user and status.user.mobile:
            message = "Your account has been whitelisted. You can now submit new applications."
            await send_notification_sms(status.user.mobile, message)

        logger.info(f"User {user_id} has been whitelisted by {whitelisted_by}")

        return {
            "user_id": str(user_id),
            "whitelisted_at": status.whitelisted_at.isoformat(),
            "reason": reason,
            "conditions": conditions,
        }

    async def manual_blacklist(
        self,
        user_id: UUID,
        blacklisted_by: UUID,
        reason: str,
        category: str = "MANUAL",
    ) -> dict:
        """Manually blacklist a user."""
        result = await self.db.execute(
            select(UserBlacklistStatus).where(UserBlacklistStatus.user_id == user_id)
        )
        status = result.scalar_one_or_none()

        if not status:
            status = UserBlacklistStatus(
                user_id=user_id,
                consecutive_rejections=0,
                total_rejections=0,
                total_approvals=0,
            )
            self.db.add(status)

        await self._apply_blacklist(
            status=status,
            reason=reason,
            category=category,
            blacklisted_by=blacklisted_by,
        )

        await self.db.flush()

        return {
            "user_id": str(user_id),
            "is_blacklisted": True,
            "blacklisted_at": status.blacklisted_at.isoformat(),
            "reason": reason,
        }
