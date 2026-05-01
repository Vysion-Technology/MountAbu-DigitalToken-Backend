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
    APPLICATION_TEMPLATE_ID = "69f0774ab51957fcc6088a84"
    TOKEN_TEMPLATE_ID = "69f075f0a665146853008054"
    COMPLAINT_TEMPLATE_ID = "69f0774ab51957fcc6088a84"

    async def send_otp(self, mobile: str, otp: str) -> bool:
...
        except Exception as e:
            logger.error(f"Exception while sending SMS: {str(e)}")
            return False

    async def send_application_sms(self, mobile: str, app_id: str, status: str) -> bool:
        """
        Send application status update SMS.
        Template: Your Application ID ##applicant_id## has been ##applicant_status##...
        """
        payload = {
            "template_id": self.APPLICATION_TEMPLATE_ID,
            "recipients": [
                {
                    "mobiles": self._format_mobile(mobile),
                    "applicant_id": app_id,
                    "applicant_status": status
                }
            ]
        }
        return await self._send_flow_sms(payload, f"Application {app_id} - {status}")

    async def send_token_sms(self, mobile: str, token_no: str, status: str) -> bool:
        """
        Send token status update SMS.
        Template: Your Digital Construction Token No ##token_no## is ##token_status##...
        """
        payload = {
            "template_id": self.TOKEN_TEMPLATE_ID,
            "recipients": [
                {
                    "mobiles": self._format_mobile(mobile),
                    "token_no": token_no,
                    "token_status": status
                }
            ]
        }
        return await self._send_flow_sms(payload, f"Token {token_no} - {status}")

    async def send_complaint_sms(self, mobile: str, complaint_id: str, status: str) -> bool:
        """
        Send complaint status update SMS.
        Template: Your Complaint ID ##complaint_id## has been ##complaint_status##...
        """
        payload = {
            "template_id": self.COMPLAINT_TEMPLATE_ID,
            "recipients": [
                {
                    "mobiles": self._format_mobile(mobile),
                    "complaint_id": complaint_id,
                    "complaint_status": status
                }
            ]
        }
        return await self._send_flow_sms(payload, f"Complaint {complaint_id} - {status}")

    def _format_mobile(self, mobile: str) -> str:
        if not mobile.startswith("91") and len(mobile) == 10:
            return f"91{mobile}"
        return mobile

    async def _send_flow_sms(self, payload: dict, log_label: str) -> bool:
        if not settings.USE_REAL_OTP:
            logger.info(f"[MOCK SMS] {log_label} would be sent to {payload['recipients'][0]['mobiles']}")
            print(f"\n[MOCK SMS] {log_label} to {payload['recipients'][0]['mobiles']}\n")
            return True

        if not settings.MSG91_AUTH_KEY:
            logger.error("MSG91_AUTH_KEY is not configured.")
            return False

        url = "https://control.msg91.com/api/v5/flow"
        headers = {
            "accept": "application/json",
            "authkey": settings.MSG91_AUTH_KEY,
            "content-type": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                response_data = response.json()
                if response.status_code == 200 and response_data.get("type") == "success":
                    logger.info(f"Successfully sent {log_label}")
                    return True
                else:
                    logger.error(f"Failed to send {log_label} via MSG91: {response_data}")
                    return False
        except Exception as e:
            logger.error(f"Exception while sending {log_label}: {str(e)}")
            return False

# Initialize a global instance
sms_service = SMSService()
