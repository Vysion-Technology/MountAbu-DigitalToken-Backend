"""NAKA checkpoint controller.

All endpoints use opaque HMAC-signed transport codes so that the
NAKA incharge never sees application IDs or applicant PII.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.transport_code import decode_transport_code, encode_transport_code
from backend.meta import UserRole
from backend.middlewares.auth import get_current_user
from backend.schemas.base.auth import UserDetails
from backend.schemas.request.application import NakaEntryCreate
from backend.schemas.response.meta import SuccessResponse
from backend.schemas.response.naka import NakaPhaseResponse, NakaMaterialSummary, NakaScheduleInfo
from backend.services.application import ApplicationService, get_application_service

router = APIRouter()


def _require_naka_role(user: UserDetails) -> None:
    """Raise 403 if user is not NAKA_INCHARGE or SUPERADMIN."""
    if user.role not in (UserRole.NAKA_INCHARGE, UserRole.SUPERADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only NAKA_INCHARGE or SUPERADMIN can access this endpoint",
        )


def _decode_or_400(transport_code: str):
    """Decode transport code or raise 400."""
    try:
        return decode_transport_code(transport_code)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or tampered transport code",
        )


@router.get("/naka/{transport_code}", response_model=NakaPhaseResponse)
async def get_naka_phase_summary(
    transport_code: str,
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> NakaPhaseResponse:
    """Get material summary for a phase. No PII is returned."""
    _require_naka_role(user)
    code_data = _decode_or_400(transport_code)

    summary = await application_service.get_phase_material_summary(
        code_data.application_id, code_data.phase
    )
    return NakaPhaseResponse(
        transport_code=transport_code,
        phase=summary["phase"],
        phase_status=summary["phase_status"],
        materials=[NakaMaterialSummary(**m) for m in summary["materials"]],
        schedule_info=NakaScheduleInfo(**summary["schedule_info"]) if summary.get("schedule_info") else None,
    )



@router.post("/naka/{transport_code}/entry", response_model=SuccessResponse)
async def create_naka_entry_by_code(
    transport_code: str,
    entry: NakaEntryCreate,
    application_service: ApplicationService = Depends(get_application_service),
    user: UserDetails = Depends(get_current_user),
) -> SuccessResponse:
    """Log a material entry at the naka checkpoint using a transport code."""
    _require_naka_role(user)
    code_data = _decode_or_400(transport_code)

    return await application_service.create_naka_entry(
        application_id=code_data.application_id,
        phase=code_data.phase,
        entry=entry,
        user_id=user.user_id,
    )
