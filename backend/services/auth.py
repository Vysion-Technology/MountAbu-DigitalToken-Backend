from typing import Optional
from backend.services.base import BaseService


class AuthService(BaseService):
    """Authentication related items."""

    async def send_otp(self, mobile: str) -> str:
        pass

    async def verify_otp(self, mobile: str, otp: str) -> str:
        pass

    async def register(self, mobile: str, name: Optional[str] = None) -> str:
        pass

    async def login(self, mobile: str, otp: str) -> str:
        pass
