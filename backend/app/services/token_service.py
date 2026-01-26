"""Token service - business logic for tokens."""

import base64
import io
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

import qrcode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import Application, Token, TokenStatus, VehicleEntry, User, UserType

logger = logging.getLogger(__name__)


class TokenService:
    """Service for token business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_tokens_for_application(
        self,
        application: Application,
        generated_by: UUID,
    ) -> List[Token]:
        """Generate phase-wise tokens for an approved application."""
        # For simplicity, generate a single token
        # In production, this would parse the estimate phases

        token_number = self._generate_token_number(application.application_number, 1)

        # Default materials (would come from estimate in production)
        materials = [
            {
                "material_type": "CEMENT",
                "material_name": "Cement (50kg bags)",
                "approved_quantity": 100,
                "consumed_quantity": 0,
                "remaining_quantity": 100,
                "unit": "bags",
            },
            {
                "material_type": "SAND",
                "material_name": "Sand",
                "approved_quantity": 10,
                "consumed_quantity": 0,
                "remaining_quantity": 10,
                "unit": "truckloads",
            },
        ]

        token = Token(
            token_number=token_number,
            application_id=application.id,
            phase_number=1,
            phase_name="Phase 1",
            materials=materials,
            status=TokenStatus.ACTIVE,
            valid_from=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc)
            + timedelta(days=settings.TOKEN_DEFAULT_VALIDITY_DAYS),
            qr_code_data=token_number,  # Simple QR data
            generated_by=generated_by,
        )
        self.db.add(token)

        logger.info(
            f"Generated token {token_number} for application {application.application_number}"
        )

        return [token]

    def _generate_token_number(self, application_number: str, phase: int) -> str:
        """Generate unique token number."""
        # Format: TKN-{app_number}-P{phase}
        return f"TKN-{application_number.replace('APP-', '')}-P{phase}"

    async def generate_qr_code(self, token_number: str) -> str:
        """Generate QR code for token and return as base64."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(token_number)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode("utf-8")

        return f"data:image/png;base64,{img_base64}"

    async def share_token(
        self,
        token_id: UUID,
        user: User,
        driver_name: str,
        driver_mobile: str,
        vehicle_number: str,
        valid_for_hours: int = 24,
        material_limit: Optional[dict] = None,
    ) -> dict:
        """Share token with a driver."""
        # Get token
        result = await self.db.execute(
            select(Token)
            .options(selectinload(Token.application))
            .where(Token.id == token_id)
        )
        token = result.scalar_one_or_none()

        if not token:
            raise ValueError("Token not found")

        # Verify ownership
        if user.user_type == UserType.APPLICANT:
            if token.application.applicant_id != user.id:
                raise ValueError("Access denied")

        # Generate share link (simplified)
        share_code = secrets.token_urlsafe(8)
        share_link = f"https://token.mountabu.gov.in/s/{share_code}"

        # In production, store share details in a separate table
        # For now, just return the share info

        logger.info(
            f"Token {token.token_number} shared with driver {driver_name} "
            f"for vehicle {vehicle_number}"
        )

        return {
            "token_number": token.token_number,
            "share_code": share_code,
            "share_link": share_link,
            "driver_name": driver_name,
            "driver_mobile": driver_mobile,
            "vehicle_number": vehicle_number,
            "valid_until": (
                datetime.now(timezone.utc) + timedelta(hours=valid_for_hours)
            ).isoformat(),
        }

    async def scan_token(
        self,
        token_qr: str,
        vehicle_number: str,
        material_type: str,
        quantity: float,
        unit: str,
        naka_location: str,
        verified_by: UUID,
        driver_mobile: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> dict:
        """Scan and validate token at Naka checkpoint."""
        # Find token
        result = await self.db.execute(
            select(Token)
            .options(
                selectinload(Token.application).selectinload(Application.applicant),
                selectinload(Token.vehicle_entries),
            )
            .where(Token.token_number == token_qr)
        )
        token = result.scalar_one_or_none()

        if not token:
            return {
                "valid": False,
                "error_reason": "INVALID",
                "message": "Token not found",
            }

        # Check status
        if token.status == TokenStatus.EXPIRED:
            return {
                "valid": False,
                "token_id": str(token.id),
                "error_reason": "EXPIRED",
                "message": "Token has expired",
            }

        if token.status == TokenStatus.CANCELLED:
            return {
                "valid": False,
                "token_id": str(token.id),
                "error_reason": "CANCELLED",
                "message": "Token has been cancelled",
            }

        # Check validity period
        now = datetime.now(timezone.utc)
        if now < token.valid_from or now > token.valid_until:
            return {
                "valid": False,
                "token_id": str(token.id),
                "error_reason": "INVALID_PERIOD",
                "message": "Token is not valid for current date",
            }

        # Check geo-bounds (optional)
        if latitude and longitude:
            if not self._is_within_bounds(latitude, longitude):
                logger.warning(f"Token scan outside bounds: {latitude}, {longitude}")
                # Just log, don't reject

        # Find material in token
        material_info = None
        for mat in token.materials:
            mat_type = mat.get("material_type") or mat.get("materialType")
            if mat_type == material_type:
                material_info = mat
                break

        if not material_info:
            return {
                "valid": False,
                "token_id": str(token.id),
                "error_reason": "INVALID_MATERIAL",
                "message": f"Material {material_type} not found in token",
            }

        # Calculate remaining quantity
        approved = material_info.get("approved_quantity") or material_info.get(
            "approvedQuantity", 0
        )
        consumed = sum(
            entry.quantity
            for entry in token.vehicle_entries
            if entry.material_type == material_type
        )
        remaining = approved - consumed

        if quantity > remaining:
            return {
                "valid": False,
                "token_id": str(token.id),
                "error_reason": "EXHAUSTED",
                "message": f"Insufficient quantity. Remaining: {remaining} {unit}",
                "previous_balance": remaining,
            }

        # Create vehicle entry
        entry = VehicleEntry(
            token_id=token.id,
            vehicle_number=vehicle_number.upper(),
            driver_mobile=driver_mobile,
            material_type=material_type,
            quantity=quantity,
            unit=unit,
            naka_location=naka_location,
            naka_coordinates={"latitude": latitude, "longitude": longitude}
            if latitude and longitude
            else None,
            verified_by=verified_by,
        )
        self.db.add(entry)

        # Update token usage
        token.usage_count += 1
        token.last_used_at = now

        # Check if all materials exhausted
        new_remaining = remaining - quantity
        if new_remaining <= 0:
            # Check all materials
            all_exhausted = True
            for mat in token.materials:
                mat_type = mat.get("material_type") or mat.get("materialType")
                mat_approved = mat.get("approved_quantity") or mat.get(
                    "approvedQuantity", 0
                )
                mat_consumed = sum(
                    e.quantity
                    for e in token.vehicle_entries
                    if e.material_type == mat_type
                )
                if mat_type == material_type:
                    mat_consumed += quantity  # Add current entry
                if mat_consumed < mat_approved:
                    all_exhausted = False
                    break

            if all_exhausted:
                token.status = TokenStatus.EXHAUSTED

        await self.db.flush()

        logger.info(
            f"Token {token.token_number} scanned at {naka_location}: "
            f"{quantity} {unit} of {material_type}"
        )

        return {
            "valid": True,
            "token_id": str(token.id),
            "entry_id": str(entry.id),
            "applicant": {
                "name": token.application.applicant.name,
                "mobile": token.application.applicant.mobile,
            },
            "property_address": token.application.property_details.get(
                "address", {}
            ).get("line1", ""),
            "material_allowed": True,
            "quantity_allowed": True,
            "previous_balance": remaining,
            "entered_quantity": quantity,
            "new_balance": remaining - quantity,
        }

    def _is_within_bounds(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within Mount Abu bounds."""
        return (
            settings.MOUNTABU_LAT_MIN <= lat <= settings.MOUNTABU_LAT_MAX
            and settings.MOUNTABU_LON_MIN <= lon <= settings.MOUNTABU_LON_MAX
        )
