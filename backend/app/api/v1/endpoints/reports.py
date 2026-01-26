"""Reporting endpoints."""

from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.deps import get_current_authority
from app.models import (
    Application,
    ApplicationStatus,
    ApplicationType,
    Token,
    TokenStatus,
    VehicleEntry,
    User,
)
from app.schemas import SuccessResponse

router = APIRouter()


@router.get("/applications", response_model=SuccessResponse)
async def get_application_report(
    current_user: Annotated[User, Depends(get_current_authority)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    group_by: str = "day",
):
    """Get application statistics report."""
    # Parse dates
    if date_from:
        start_date = datetime.fromisoformat(date_from)
    else:
        start_date = datetime.now() - timedelta(days=30)

    if date_to:
        end_date = datetime.fromisoformat(date_to)
    else:
        end_date = datetime.now()

    # Get summary statistics
    summary_result = await db.execute(
        select(
            func.count(Application.id).label("total"),
            func.count(Application.id)
            .filter(Application.status == ApplicationStatus.APPROVED)
            .label("approved"),
            func.count(Application.id)
            .filter(Application.status == ApplicationStatus.REJECTED)
            .label("rejected"),
            func.count(Application.id)
            .filter(
                Application.status.in_(
                    [
                        ApplicationStatus.SUBMITTED,
                        ApplicationStatus.SDM_REVIEW,
                        ApplicationStatus.CMS_REVIEW,
                        ApplicationStatus.JEN_INSPECTION,
                    ]
                )
            )
            .label("pending"),
        ).where(
            Application.submitted_at >= start_date,
            Application.submitted_at <= end_date,
        )
    )
    summary = summary_result.one()

    # Get by type
    type_result = await db.execute(
        select(
            Application.application_type,
            func.count(Application.id),
        )
        .where(
            Application.submitted_at >= start_date,
            Application.submitted_at <= end_date,
        )
        .group_by(Application.application_type)
    )
    by_type = {row[0].value: row[1] for row in type_result.all()}

    # Calculate approval rate
    approval_rate = 0
    if summary.approved + summary.rejected > 0:
        approval_rate = round(
            (summary.approved / (summary.approved + summary.rejected)) * 100, 2
        )

    return SuccessResponse(
        data={
            "report_period": {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
            "summary": {
                "total_applications": summary.total,
                "approved": summary.approved,
                "rejected": summary.rejected,
                "pending": summary.pending,
                "approval_rate": approval_rate,
            },
            "by_type": by_type,
        }
    )


@router.get("/tokens", response_model=SuccessResponse)
async def get_token_report(
    current_user: Annotated[User, Depends(get_current_authority)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Get token usage statistics."""
    # Parse dates
    if date_from:
        start_date = datetime.fromisoformat(date_from)
    else:
        start_date = datetime.now() - timedelta(days=30)

    if date_to:
        end_date = datetime.fromisoformat(date_to)
    else:
        end_date = datetime.now()

    # Get token summary
    token_result = await db.execute(
        select(
            func.count(Token.id).label("total"),
            func.count(Token.id)
            .filter(Token.status == TokenStatus.ACTIVE)
            .label("active"),
            func.count(Token.id)
            .filter(Token.status == TokenStatus.EXHAUSTED)
            .label("exhausted"),
            func.count(Token.id)
            .filter(Token.status == TokenStatus.EXPIRED)
            .label("expired"),
        ).where(
            Token.created_at >= start_date,
            Token.created_at <= end_date,
        )
    )
    token_summary = token_result.one()

    # Get usage count
    usage_result = await db.execute(
        select(func.count(VehicleEntry.id)).where(
            VehicleEntry.created_at >= start_date,
            VehicleEntry.created_at <= end_date,
        )
    )
    total_usage = usage_result.scalar()

    # Get material consumption
    material_result = await db.execute(
        select(
            VehicleEntry.material_type,
            func.sum(VehicleEntry.quantity),
            VehicleEntry.unit,
        )
        .where(
            VehicleEntry.created_at >= start_date,
            VehicleEntry.created_at <= end_date,
        )
        .group_by(VehicleEntry.material_type, VehicleEntry.unit)
    )
    materials = [
        {
            "material": row[0],
            "quantity": float(row[1]) if row[1] else 0,
            "unit": row[2],
        }
        for row in material_result.all()
    ]

    return SuccessResponse(
        data={
            "report_period": {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
            "summary": {
                "tokens_issued": token_summary.total,
                "tokens_active": token_summary.active,
                "tokens_exhausted": token_summary.exhausted,
                "tokens_expired": token_summary.expired,
                "total_usage_events": total_usage,
            },
            "materials_summary": materials,
        }
    )


@router.get("/vehicles", response_model=SuccessResponse)
async def get_vehicle_report(
    current_user: Annotated[User, Depends(get_current_authority)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    naka_location: Optional[str] = None,
):
    """Get vehicle entry statistics."""
    # Parse dates
    if date_from:
        start_date = datetime.fromisoformat(date_from)
    else:
        start_date = datetime.now() - timedelta(days=7)

    if date_to:
        end_date = datetime.fromisoformat(date_to)
    else:
        end_date = datetime.now()

    # Build query
    query = select(
        VehicleEntry.naka_location,
        VehicleEntry.material_type,
        func.count(VehicleEntry.id).label("entry_count"),
        func.sum(VehicleEntry.quantity).label("total_quantity"),
        VehicleEntry.unit,
        func.count(func.distinct(VehicleEntry.vehicle_number)).label("unique_vehicles"),
    ).where(
        VehicleEntry.created_at >= start_date,
        VehicleEntry.created_at <= end_date,
    )

    if naka_location:
        query = query.where(VehicleEntry.naka_location == naka_location)

    query = query.group_by(
        VehicleEntry.naka_location,
        VehicleEntry.material_type,
        VehicleEntry.unit,
    )

    result = await db.execute(query)
    entries = result.all()

    return SuccessResponse(
        data={
            "report_period": {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
            "entries": [
                {
                    "naka_location": row.naka_location,
                    "material_type": row.material_type,
                    "entry_count": row.entry_count,
                    "total_quantity": float(row.total_quantity)
                    if row.total_quantity
                    else 0,
                    "unit": row.unit,
                    "unique_vehicles": row.unique_vehicles,
                }
                for row in entries
            ],
        }
    )
