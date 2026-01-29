from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dbmodels.user import User, ActiveUserOTP
from backend.meta import UserRole


class UserDAO:
    async def get_by_mobile(self, session: AsyncSession, mobile: str) -> Optional[User]:
        stmt = select(User).where(User.mobile == mobile)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(
        self, session: AsyncSession, username: str
    ) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, session: AsyncSession, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        session: AsyncSession,
        mobile: str,
        role: UserRole,
        name: str,
        password: Optional[str] = None,
        username: Optional[str] = None,
    ) -> User:
        user = User(
            mobile=mobile, role=role, name=name, password=password, username=username
        )
        session.add(user)
        # Flush to get ID, but commit should be handled by service/controller
        await session.flush()
        return user

    async def get_otp_record(
        self, session: AsyncSession, mobile: str
    ) -> Optional[ActiveUserOTP]:
        # Get the latest valid OTP
        stmt = (
            select(ActiveUserOTP)
            .where(ActiveUserOTP.mobile == mobile)
            .order_by(ActiveUserOTP.id.desc())
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_otp(self, session: AsyncSession, mobile: str, otp: str):
        otp_record = ActiveUserOTP(mobile=mobile, otp=otp)
        session.add(otp_record)
        await session.commit()
