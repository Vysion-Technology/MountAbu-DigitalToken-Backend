from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dbmodels.user import User, ActiveUserOTP
from backend.meta import UserRole, JurisdictionZone


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
        name: str = "",
        password: Optional[str] = None,
        username: Optional[str] = None,
        jurisdiction_zone: Optional[JurisdictionZone] = None,
    ) -> User:
        user = User(
            mobile=mobile,
            role=role,
            name=name,
            password=password,
            username=username,
            jurisdiction_zone=jurisdiction_zone,
        )
        session.add(user)
        # Flush to get ID, but commit should be handled by service/controller
        await session.flush()
        return user

    async def get_otp_record(
        self, session: AsyncSession, mobile: str
    ) -> Optional[ActiveUserOTP]:
        # Get the latest OTP (regardless of expiry, for verification purposes)
        stmt = (
            select(ActiveUserOTP)
            .where(ActiveUserOTP.mobile == mobile)
            .order_by(ActiveUserOTP.id.desc())
        )
        result = await session.execute(stmt)
        return max(result.scalars().all(), key=lambda x: x.valid_till, default=None)

    async def get_valid_otp_record(
        self, session: AsyncSession, mobile: str
    ) -> Optional[ActiveUserOTP]:
        """Get an existing OTP that hasn't expired yet."""
        from datetime import datetime

        stmt = (
            select(ActiveUserOTP)
            .where(ActiveUserOTP.mobile == mobile)
            .where(ActiveUserOTP.valid_till > datetime.now())
            .order_by(ActiveUserOTP.id.desc())
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_otp(self, session: AsyncSession, mobile: str, otp: str):
        otp_record = ActiveUserOTP(mobile=mobile, otp=otp)
        session.add(otp_record)
        await session.commit()

    async def delete_otp_records(self, session: AsyncSession, mobile: str):
        """Delete all OTP records for a mobile number."""
        from sqlalchemy import delete
        stmt = delete(ActiveUserOTP).where(ActiveUserOTP.mobile == mobile)
        await session.execute(stmt)
        await session.commit()

    async def get_users_filtered(
        self, session: AsyncSession, is_citizen: bool
    ) -> Sequence[User]:
        stmt = select(User)
        if is_citizen:
            stmt = stmt.where(User.role == UserRole.CITIZEN)
        else:
            stmt = stmt.where(User.role != UserRole.CITIZEN)

        # Order by most recent first, or name? Let's do name for now, or ID desc
        stmt = stmt.order_by(User.id.desc())

        result = await session.execute(stmt)
        return result.scalars().all()
