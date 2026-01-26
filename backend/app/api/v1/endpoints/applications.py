"""Application management endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_authority
from app.models import (
    Application,
    ApplicationStatus,
    ApplicationTimeline,
    ApplicationType,
    User,
    UserType,
)
from app.schemas import (
    ApplicationCreate,
    ApplicationApprove,
    ApplicationReject,
    ApplicationForward,
    SuccessResponse,
)
from app.services.application_service import ApplicationService
from app.services.blacklist_service import BlacklistService

router = APIRouter()


def generate_application_number() -> str:
    """Generate unique application number."""
    import random

    year = datetime.now().year
    random_part = random.randint(10000, 99999)
    return f"APP-{year}-{random_part}"


@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    request: ApplicationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create new application."""
    # Check if user is blacklisted
    blacklist_service = BlacklistService(db)
    is_blacklisted, reason = await blacklist_service.check_blacklist(current_user.id)

    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "USER_BLACKLISTED",
                "message": reason,
            },
        )

    # Create application
    application = Application(
        application_number=generate_application_number(),
        application_type=ApplicationType(request.application_type),
        applicant_id=current_user.id,
        property_details=request.property_details.model_dump(),
        construction_details=request.construction_details.model_dump(),
        status=ApplicationStatus.SUBMITTED,
        current_authority_role="SDM",
        terms_accepted=request.terms_accepted,
        declaration_accepted=request.declaration_accepted,
        sla_deadline=datetime.now(timezone.utc)
        + timedelta(days=settings.APPLICATION_SLA_DAYS),
    )
    db.add(application)
    await db.flush()

    # Add timeline entry
    timeline = ApplicationTimeline(
        application_id=application.id,
        status=ApplicationStatus.SUBMITTED.value,
        action="SUBMITTED",
        actor_id=current_user.id,
        actor_name=current_user.name,
        actor_role="APPLICANT",
        comments="Application submitted",
    )
    db.add(timeline)

    return SuccessResponse(
        message="Application submitted successfully",
        data={
            "application_id": str(application.id),
            "application_number": application.application_number,
            "status": application.status.value,
            "submitted_at": application.submitted_at.isoformat(),
        },
    )


@router.get("", response_model=SuccessResponse)
async def list_applications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Optional[str] = Query(None, alias="status"),
    type_filter: Optional[str] = Query(None, alias="type"),
    page: int = 1,
    limit: int = 20,
):
    """List applications (filtered by user type)."""
    # Build base query
    if current_user.user_type == UserType.APPLICANT:
        # Applicants see only their applications
        query = select(Application).where(
            Application.applicant_id == current_user.id,
            Application.is_deleted == False,
        )
    else:
        # Authorities see applications assigned to them or all (depending on role)
        query = select(Application).where(Application.is_deleted == False)

        # Filter by current authority role if needed
        if current_user.role:
            query = query.where(
                Application.current_authority_role == current_user.role.name.value
            )

    # Apply filters
    if status_filter:
        query = query.where(Application.status == ApplicationStatus(status_filter))
    if type_filter:
        query = query.where(
            Application.application_type == ApplicationType(type_filter)
        )

    # Get total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    # Paginate and order
    query = (
        query.options(selectinload(Application.applicant))
        .order_by(Application.submitted_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(query)
    applications = result.scalars().all()

    return SuccessResponse(
        data={
            "applications": [
                {
                    "id": str(app.id),
                    "application_number": app.application_number,
                    "application_type": app.application_type.value,
                    "status": app.status.value,
                    "applicant": {
                        "name": app.applicant.name,
                        "mobile": f"****{app.applicant.mobile[-4:]}"
                        if app.applicant.mobile
                        else None,
                    },
                    "property_address": app.property_details.get("address", {}).get(
                        "line1", ""
                    ),
                    "submitted_at": app.submitted_at.isoformat(),
                    "current_authority": app.current_authority_role,
                }
                for app in applications
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
            },
        }
    )


@router.get("/{application_id}", response_model=SuccessResponse)
async def get_application(
    application_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get application details."""
    result = await db.execute(
        select(Application)
        .options(
            selectinload(Application.applicant),
            selectinload(Application.documents),
            selectinload(Application.tokens),
            selectinload(Application.timeline),
        )
        .where(Application.id == application_id, Application.is_deleted == False)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    # Check access
    if current_user.user_type == UserType.APPLICANT:
        if application.applicant_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    return SuccessResponse(
        data={
            "id": str(application.id),
            "application_number": application.application_number,
            "application_type": application.application_type.value,
            "status": application.status.value,
            "applicant": {
                "id": str(application.applicant.id),
                "name": application.applicant.name,
                "mobile": application.applicant.mobile,
                "email": application.applicant.email,
            },
            "property_details": application.property_details,
            "construction_details": application.construction_details,
            "current_authority_role": application.current_authority_role,
            "sla_deadline": application.sla_deadline.isoformat()
            if application.sla_deadline
            else None,
            "documents": [
                {
                    "id": str(doc.id),
                    "type": doc.document_type,
                    "name": doc.original_name,
                    "verified": doc.verified,
                }
                for doc in application.documents
            ],
            "tokens": [
                {
                    "id": str(token.id),
                    "token_number": token.token_number,
                    "phase": token.phase_number,
                    "status": token.status.value,
                }
                for token in application.tokens
            ],
            "timeline": [
                {
                    "status": entry.status,
                    "action": entry.action,
                    "actor_name": entry.actor_name,
                    "actor_role": entry.actor_role,
                    "comments": entry.comments,
                    "timestamp": entry.timestamp.isoformat(),
                }
                for entry in sorted(application.timeline, key=lambda x: x.timestamp)
            ],
            "submitted_at": application.submitted_at.isoformat(),
            "approved_at": application.approved_at.isoformat()
            if application.approved_at
            else None,
            "rejected_at": application.rejected_at.isoformat()
            if application.rejected_at
            else None,
            "rejection_reason": application.rejection_reason,
        }
    )


@router.post("/{application_id}/approve", response_model=SuccessResponse)
async def approve_application(
    application_id: UUID,
    request: ApplicationApprove,
    current_user: Annotated[User, Depends(get_current_authority)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Approve application (SDM/CMS only)."""
    app_service = ApplicationService(db)
    result = await app_service.approve_application(
        application_id=application_id,
        authority=current_user,
        comments=request.comments,
        conditions=request.conditions,
        generate_tokens=request.generate_tokens,
    )
    return SuccessResponse(message="Application approved", data=result)


@router.post("/{application_id}/reject", response_model=SuccessResponse)
async def reject_application(
    application_id: UUID,
    request: ApplicationReject,
    current_user: Annotated[User, Depends(get_current_authority)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reject application."""
    app_service = ApplicationService(db)
    blacklist_service = BlacklistService(db)

    result = await app_service.reject_application(
        application_id=application_id,
        authority=current_user,
        reason=request.reason,
        comments=request.comments,
        category=request.rejection_category,
    )

    # Process blacklist logic
    blacklist_result = await blacklist_service.process_rejection(
        user_id=result["applicant_id"],
        application_id=application_id,
        rejected_by=current_user.id,
        rejected_by_role=current_user.role.name.value
        if current_user.role
        else "UNKNOWN",
        reason=request.reason,
        category=request.rejection_category,
        comments=request.comments,
    )

    result["blacklist_status"] = blacklist_result

    return SuccessResponse(message="Application rejected", data=result)


@router.post("/{application_id}/forward", response_model=SuccessResponse)
async def forward_application(
    application_id: UUID,
    request: ApplicationForward,
    current_user: Annotated[User, Depends(get_current_authority)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Forward application to next authority."""
    app_service = ApplicationService(db)
    result = await app_service.forward_application(
        application_id=application_id,
        authority=current_user,
        forward_to=request.forward_to,
        comments=request.comments,
    )
    return SuccessResponse(message="Application forwarded", data=result)
