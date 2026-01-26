"""Application service - business logic for applications."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import (
    Application,
    ApplicationStatus,
    ApplicationTimeline,
    User,
    Token,
    TokenStatus,
)
from app.services.blacklist_service import BlacklistService
from app.services.token_service import TokenService

logger = logging.getLogger(__name__)


class ApplicationService:
    """Service for application business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_application(self, application_id: UUID) -> Optional[Application]:
        """Get application by ID."""
        result = await self.db.execute(
            select(Application)
            .options(selectinload(Application.applicant))
            .where(Application.id == application_id, Application.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def approve_application(
        self,
        application_id: UUID,
        authority: User,
        comments: Optional[str] = None,
        conditions: Optional[List[str]] = None,
        generate_tokens: bool = True,
    ) -> dict:
        """Approve application and optionally generate tokens."""
        application = await self.get_application(application_id)

        if not application:
            raise ValueError("Application not found")

        # Validate authority can approve
        if authority.role and authority.role.name.value not in [
            "SDM",
            "CMS_UIT",
            "CMS_ULB",
        ]:
            raise ValueError("Only SDM/CMS can approve applications")

        # Update application
        application.status = ApplicationStatus.APPROVED
        application.approved_at = datetime.now(timezone.utc)
        application.approved_by = authority.id
        application.approval_conditions = conditions
        application.last_action_at = datetime.now(timezone.utc)

        # Add timeline entry
        timeline = ApplicationTimeline(
            application_id=application.id,
            status=ApplicationStatus.APPROVED.value,
            action="APPROVED",
            actor_id=authority.id,
            actor_name=authority.name,
            actor_role=authority.role.name.value if authority.role else None,
            comments=comments,
        )
        self.db.add(timeline)

        # Reset consecutive rejections for the applicant
        blacklist_service = BlacklistService(self.db)
        await blacklist_service.reset_on_approval(application.applicant_id)

        # Generate tokens if requested
        tokens_generated = []
        if generate_tokens:
            token_service = TokenService(self.db)
            tokens_generated = await token_service.generate_tokens_for_application(
                application=application,
                generated_by=authority.id,
            )
            application.status = ApplicationStatus.TOKENS_ISSUED

        await self.db.flush()

        logger.info(
            f"Application {application.application_number} approved by {authority.name}"
        )

        return {
            "application_id": str(application.id),
            "application_number": application.application_number,
            "status": application.status.value,
            "approved_at": application.approved_at.isoformat(),
            "tokens_generated": len(tokens_generated),
            "tokens": [
                {"token_number": t.token_number, "phase": t.phase_number}
                for t in tokens_generated
            ],
        }

    async def reject_application(
        self,
        application_id: UUID,
        authority: User,
        reason: str,
        comments: str,
        category: str,
    ) -> dict:
        """Reject application."""
        application = await self.get_application(application_id)

        if not application:
            raise ValueError("Application not found")

        # Update application
        application.status = ApplicationStatus.REJECTED
        application.rejected_at = datetime.now(timezone.utc)
        application.rejection_reason = reason
        application.rejection_category = category
        application.last_action_at = datetime.now(timezone.utc)

        # Add timeline entry
        timeline = ApplicationTimeline(
            application_id=application.id,
            status=ApplicationStatus.REJECTED.value,
            action="REJECTED",
            actor_id=authority.id,
            actor_name=authority.name,
            actor_role=authority.role.name.value if authority.role else None,
            comments=comments,
            metadata={"reason": reason, "category": category},
        )
        self.db.add(timeline)

        await self.db.flush()

        logger.info(
            f"Application {application.application_number} rejected by {authority.name}"
        )

        return {
            "application_id": str(application.id),
            "application_number": application.application_number,
            "status": application.status.value,
            "rejected_at": application.rejected_at.isoformat(),
            "applicant_id": application.applicant_id,
        }

    async def forward_application(
        self,
        application_id: UUID,
        authority: User,
        forward_to: str,
        comments: Optional[str] = None,
    ) -> dict:
        """Forward application to next authority."""
        application = await self.get_application(application_id)

        if not application:
            raise ValueError("Application not found")

        # Validate authority can forward
        if authority.role and not authority.role.can_forward:
            raise ValueError("This authority cannot forward applications")

        # Map forward_to to status
        status_map = {
            "SDM": ApplicationStatus.SDM_REVIEW,
            "CMS": ApplicationStatus.CMS_REVIEW,
            "CMS_UIT": ApplicationStatus.CMS_REVIEW,
            "CMS_ULB": ApplicationStatus.CMS_REVIEW,
            "JEN": ApplicationStatus.JEN_INSPECTION,
            "LAND": ApplicationStatus.LAND_VERIFICATION,
            "LEGAL": ApplicationStatus.LEGAL_VERIFICATION,
            "ATP": ApplicationStatus.ATP_VERIFICATION,
        }

        new_status = status_map.get(forward_to.upper())
        if not new_status:
            raise ValueError(f"Invalid forward target: {forward_to}")

        # Update application
        previous_role = application.current_authority_role
        application.status = new_status
        application.current_authority_role = forward_to.upper()
        application.last_action_at = datetime.now(timezone.utc)

        # Add timeline entry
        timeline = ApplicationTimeline(
            application_id=application.id,
            status=new_status.value,
            action="FORWARDED",
            actor_id=authority.id,
            actor_name=authority.name,
            actor_role=authority.role.name.value if authority.role else None,
            comments=comments,
            metadata={"from": previous_role, "to": forward_to.upper()},
        )
        self.db.add(timeline)

        await self.db.flush()

        logger.info(
            f"Application {application.application_number} forwarded "
            f"from {previous_role} to {forward_to} by {authority.name}"
        )

        return {
            "application_id": str(application.id),
            "application_number": application.application_number,
            "status": application.status.value,
            "current_authority": application.current_authority_role,
            "forwarded_by": authority.name,
        }
