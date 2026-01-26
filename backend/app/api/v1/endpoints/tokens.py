"""Token management endpoints."""

from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_authority
from app.models import Token, TokenStatus, Application, User, UserType, VehicleEntry
from app.schemas import TokenScan, TokenScanResponse, TokenShare, SuccessResponse
from app.services.token_service import TokenService

router = APIRouter()


@router.get("", response_model=SuccessResponse)
async def list_tokens(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    application_id: Optional[UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = 1,
    limit: int = 20,
):
    """List tokens (filtered by user)."""
    # Build query
    if current_user.user_type == UserType.APPLICANT:
        # Get tokens for applicant's applications
        query = (
            select(Token)
            .join(Application)
            .where(Application.applicant_id == current_user.id)
        )
    else:
        # Authorities see all tokens
        query = select(Token)

    if application_id:
        query = query.where(Token.application_id == application_id)

    if status_filter:
        query = query.where(Token.status == TokenStatus(status_filter))

    # Count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    # Paginate
    query = (
        query.options(selectinload(Token.application))
        .order_by(Token.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(query)
    tokens = result.scalars().all()

    return SuccessResponse(
        data={
            "tokens": [
                {
                    "id": str(token.id),
                    "token_number": token.token_number,
                    "application_number": token.application.application_number,
                    "phase_number": token.phase_number,
                    "phase_name": token.phase_name,
                    "status": token.status.value,
                    "materials": token.materials,
                    "valid_from": token.valid_from.isoformat(),
                    "valid_until": token.valid_until.isoformat(),
                    "usage_count": token.usage_count,
                }
                for token in tokens
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
            },
        }
    )


@router.get("/{token_id}", response_model=SuccessResponse)
async def get_token(
    token_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get token details with QR code."""
    result = await db.execute(
        select(Token)
        .options(
            selectinload(Token.application).selectinload(Application.applicant),
            selectinload(Token.vehicle_entries),
        )
        .where(Token.id == token_id)
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )

    # Check access for applicants
    if current_user.user_type == UserType.APPLICANT:
        if token.application.applicant_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    # Generate QR code
    token_service = TokenService(db)
    qr_base64 = await token_service.generate_qr_code(token.token_number)

    # Calculate remaining quantities
    materials_with_usage = []
    for material in token.materials:
        material_type = material.get("material_type") or material.get("materialType")
        approved = material.get("approved_quantity") or material.get(
            "approvedQuantity", 0
        )

        # Sum consumed quantity from vehicle entries
        consumed = sum(
            entry.quantity
            for entry in token.vehicle_entries
            if entry.material_type == material_type
        )

        materials_with_usage.append(
            {
                "material_type": material_type,
                "material_name": material.get("material_name")
                or material.get("materialName"),
                "approved_quantity": approved,
                "consumed_quantity": consumed,
                "remaining_quantity": approved - consumed,
                "unit": material.get("unit"),
            }
        )

    return SuccessResponse(
        data={
            "id": str(token.id),
            "token_number": token.token_number,
            "application": {
                "id": str(token.application.id),
                "application_number": token.application.application_number,
                "applicant_name": token.application.applicant.name,
            },
            "phase_number": token.phase_number,
            "phase_name": token.phase_name,
            "status": token.status.value,
            "materials": materials_with_usage,
            "valid_from": token.valid_from.isoformat(),
            "valid_until": token.valid_until.isoformat(),
            "qr_code": qr_base64,
            "shareable_link": f"https://token.mountabu.gov.in/v/{token.token_number}",
            "usage_count": token.usage_count,
            "usage_history": [
                {
                    "entry_id": str(entry.id),
                    "vehicle_number": entry.vehicle_number,
                    "material": entry.material_type,
                    "quantity": float(entry.quantity),
                    "unit": entry.unit,
                    "naka_location": entry.naka_location,
                    "entry_time": entry.created_at.isoformat(),
                }
                for entry in token.vehicle_entries
            ],
        }
    )


@router.post("/{token_id}/share", response_model=SuccessResponse)
async def share_token(
    token_id: UUID,
    request: TokenShare,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Share token with driver."""
    token_service = TokenService(db)
    result = await token_service.share_token(
        token_id=token_id,
        user=current_user,
        driver_name=request.driver_name,
        driver_mobile=request.driver_mobile,
        vehicle_number=request.vehicle_number,
        valid_for_hours=request.valid_for_hours,
        material_limit=request.material_limit,
    )
    return SuccessResponse(message="Token shared successfully", data=result)


@router.post("/scan", response_model=SuccessResponse)
async def scan_token(
    request: TokenScan,
    current_user: Annotated[User, Depends(get_current_authority)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Scan and validate token at Naka checkpoint."""
    token_service = TokenService(db)

    # Verify the user is a Naka authority
    if current_user.role and current_user.role.name.value != "NAKA":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Naka incharge can scan tokens",
        )

    result = await token_service.scan_token(
        token_qr=request.token_qr,
        vehicle_number=request.vehicle_number,
        driver_mobile=request.driver_mobile,
        material_type=request.material_type,
        quantity=request.quantity,
        unit=request.unit,
        naka_location=request.naka_location,
        latitude=request.latitude,
        longitude=request.longitude,
        verified_by=current_user.id,
    )

    return SuccessResponse(data=result)
