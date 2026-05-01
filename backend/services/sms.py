import logging
import httpx
from backend.config import settings
from backend.services.base import BaseService

logger = logging.getLogger(__name__)

class SMSService(BaseService):
    """
    Service to handle sending SMS notifications via MSG91.
    """
    
    OTP_TEMPLATE_ID = "69edd13d2ee1bac60804bdb2"

    async def send_otp(self, mobile: str, otp: str) -> bool:
        """
        Send OTP to the given mobile number using MSG91 Flow API.
        """
        if not settings.USE_REAL_OTP:
            logger.info(f"[MOCK SMS] Would send OTP {otp} to {mobile}")
            print(f"\n[MOCK SMS] OTP for {mobile}: {otp}\n")
            return True

        if not settings.MSG91_AUTH_KEY:
            logger.error("MSG91_AUTH_KEY is not configured. Cannot send real SMS.")
            return False

        url = "https://control.msg91.com/api/v5/flow"
        headers = {
            "accept": "application/json",
            "authkey": settings.MSG91_AUTH_KEY,
            "content-type": "application/json"
        }
        
        # Ensure mobile has country code if not already present (defaulting to 91 as per example)
        if not mobile.startswith("91") and len(mobile) == 10:
            formatted_mobile = f"91{mobile}"
        else:
            formatted_mobile = mobile

        payload = {
            "template_id": self.OTP_TEMPLATE_ID,
            "short_url": "0",
            "realTimeResponse": "1",
            "recipients": [
                {
                    "mobiles": formatted_mobile,
                    "OTP": otp
                }
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                response_data = response.json()
                
                if response.status_code == 200 and response_data.get("type") == "success":
                    logger.info(f"Successfully sent OTP to {mobile}")
                    return True
                else:
                    logger.error(f"Failed to send SMS via MSG91: {response_data}")
                    return False
        except Exception as e:
            logger.error(f"Exception while sending SMS: {str(e)}")
            return False

# Initialize a global instance
sms_service = SMSService()
