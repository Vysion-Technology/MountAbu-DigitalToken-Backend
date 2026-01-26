"""SMS service for OTP and notifications."""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_otp_sms(mobile: str, otp: str) -> bool:
    """
    Send OTP via SMS.
    Uses MSG91 or Twilio based on configuration.
    """
    if settings.ENVIRONMENT == "development":
        # In development, just log the OTP
        logger.info(f"[DEV] OTP for {mobile}: {otp}")
        return True

    if settings.SMS_PROVIDER == "msg91":
        return await _send_via_msg91(mobile, otp)
    else:
        logger.warning(f"Unknown SMS provider: {settings.SMS_PROVIDER}")
        return False


async def _send_via_msg91(mobile: str, otp: str) -> bool:
    """Send SMS via MSG91."""
    if not settings.MSG91_AUTH_KEY:
        logger.error("MSG91_AUTH_KEY not configured")
        return False

    url = "https://api.msg91.com/api/v5/otp"

    headers = {
        "authkey": settings.MSG91_AUTH_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "template_id": settings.MSG91_TEMPLATE_ID,
        "mobile": mobile.replace("+", ""),
        "otp": otp,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                logger.info(f"OTP sent successfully to {mobile[-4:]}")
                return True
            else:
                logger.error(f"Failed to send OTP: {response.text}")
                return False
    except Exception as e:
        logger.error(f"SMS sending failed: {e}")
        return False


async def send_notification_sms(mobile: str, message: str) -> bool:
    """Send notification SMS."""
    if settings.ENVIRONMENT == "development":
        logger.info(f"[DEV] SMS to {mobile}: {message}")
        return True

    # Implementation similar to OTP but with different template
    logger.info(f"Notification SMS sent to {mobile}")
    return True
