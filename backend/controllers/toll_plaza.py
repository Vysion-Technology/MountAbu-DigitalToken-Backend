"""Toll Plaza integration controller."""

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from backend.config import settings
from backend.core.transport_code import decode_transport_code
from backend.schemas.request.toll_plaza import TollPlazaVerifyRequest
from backend.schemas.response.toll_plaza import TollPlazaVerifyResponse
from backend.services.application import ApplicationService, get_application_service

router = APIRouter()

# API Key security scheme for Toll Plaza integration
api_key_header = APIKeyHeader(name="X-Plaza-API-Key", auto_error=True)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Validate the incoming request's API Key against the configured secret."""
    if api_key != settings.TOLL_PLAZA_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Toll Plaza API Key",
        )
    return api_key


def _decode_or_400(transport_code: str):
    """Decode transport code or raise HTTP 400."""
    try:
        return decode_transport_code(transport_code)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or tampered transport code",
        )


@router.post(
    "/toll-plaza/verify",
    response_model=TollPlazaVerifyResponse,
    summary="Verify vehicle entry at toll plaza",
    description="Validates a vehicle entry logged at the Naka checkpoint and marks it as verified."
)
async def verify_toll_plaza_entry(
    request: TollPlazaVerifyRequest,
    api_key: str = Depends(verify_api_key),
    application_service: ApplicationService = Depends(get_application_service),
) -> TollPlazaVerifyResponse:
    """Validate a Naka vehicle entry using the vehicle plate and transport code."""
    # Decode the cryptographic transport code
    code_data = _decode_or_400(request.transport_code)

    # Perform the verification and return result
    result = await application_service.verify_toll_plaza_entry(
        application_id=code_data.application_id,
        phase=code_data.phase,
        vehicle_number=request.vehicle_number,
    )

    return TollPlazaVerifyResponse.model_validate(result)
