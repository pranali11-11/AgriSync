import logging
from abc import ABC, abstractmethod
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseSMSProvider(ABC):
    """Abstract interface for SMS delivery providers."""

    @abstractmethod
    async def send_otp(self, phone: str, otp: str) -> bool:
        """Send a 6-digit OTP code to the target phone number."""
        pass


class ConsoleSMSProvider(BaseSMSProvider):
    """Local development SMS provider that logs OTP to stdout/logger."""

    async def send_otp(self, phone: str, otp: str) -> bool:
        message = f"[SMS Dev] Sending OTP {otp} to {phone}"
        logger.info(message)
        print(f"\n========================================\n{message}\n========================================\n", flush=True)
        return True


class TwilioSMSProvider(BaseSMSProvider):
    """Twilio SMS delivery provider using Twilio REST API via HTTPX."""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None
    ):
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_number = from_number or settings.TWILIO_FROM_NUMBER

    async def send_otp(self, phone: str, otp: str) -> bool:
        if not self.account_sid or not self.auth_token or not self.from_number:
            logger.warning("Twilio credentials missing. Falling back to console log.")
            return await ConsoleSMSProvider().send_otp(phone, otp)

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        # Ensure phone has leading + if international
        to_phone = phone if phone.startswith("+") else f"+91{phone.lstrip('0')}"
        body = f"Your AgriSync verification code is {otp}. Valid for 5 minutes."

        data = {
            "From": self.from_number,
            "To": to_phone,
            "Body": body
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, data=data, auth=(self.account_sid, self.auth_token))
                if resp.status_code in (200, 201):
                    logger.info("Successfully sent OTP via Twilio to %s", to_phone)
                    return True
                else:
                    logger.error("Twilio error response [%s]: %s", resp.status_code, resp.text)
                    return False
        except Exception as exc:
            logger.error("Failed to send OTP via Twilio: %s", exc)
            return False


class MSG91SMSProvider(BaseSMSProvider):
    """MSG91 SMS delivery provider using MSG91 OTP API via HTTPX."""

    def __init__(
        self,
        auth_key: Optional[str] = None,
        template_id: Optional[str] = None
    ):
        self.auth_key = auth_key or settings.MSG91_AUTH_KEY
        self.template_id = template_id or settings.MSG91_TEMPLATE_ID

    async def send_otp(self, phone: str, otp: str) -> bool:
        if not self.auth_key:
            logger.warning("MSG91 auth key missing. Falling back to console log.")
            return await ConsoleSMSProvider().send_otp(phone, otp)

        # Standardize Indian phone number for MSG91 (e.g. 919876543210)
        clean_phone = phone.replace("+", "").lstrip("0")
        if len(clean_phone) == 10:
            clean_phone = f"91{clean_phone}"

        url = "https://api.msg91.com/api/v5/otp"
        params = {
            "template_id": self.template_id,
            "mobile": clean_phone,
            "authkey": self.auth_key,
            "otp": otp
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    logger.info("Successfully sent OTP via MSG91 to %s", clean_phone)
                    return True
                else:
                    logger.error("MSG91 error response [%s]: %s", resp.status_code, resp.text)
                    return False
        except Exception as exc:
            logger.error("Failed to send OTP via MSG91: %s", exc)
            return False


def get_sms_provider() -> BaseSMSProvider:
    """Factory returning the appropriate SMS provider based on configuration."""
    provider_name = (settings.SMS_PROVIDER or "").lower()

    if provider_name == "twilio" and settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
        return TwilioSMSProvider()
    elif provider_name == "msg91" and settings.MSG91_AUTH_KEY:
        return MSG91SMSProvider()
    elif settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
        return TwilioSMSProvider()
    elif settings.MSG91_AUTH_KEY:
        return MSG91SMSProvider()

    return ConsoleSMSProvider()
