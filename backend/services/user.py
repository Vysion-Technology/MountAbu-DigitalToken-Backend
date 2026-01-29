from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import get_password_hash
from backend.dao.user import UserDAO
from backend.dbmodels.user import User
from backend.meta import UserRole


class UserService:
    def __init__(self):
        self.user_dao = UserDAO()

    async def create_user(
        self,
        session: AsyncSession,
        mobile: str,
        name: str,
        role: UserRole,
        password: Optional[str] = None,
        username: Optional[str] = None,
    ) -> User:
        hashed_password = get_password_hash(password) if password else None
        user = await self.user_dao.create_user(
            session,
            mobile=mobile,
            name=name,
            role=role,
            password=hashed_password,
            username=username,
        )
        # We might want to commit here if this is a standalone action, or let the caller (API) commit.
        # Assuming API handles commit via dependency or middleware, but explicit flush was done.
        # Let's simple return user.
        return user

    async def get_user_by_mobile(
        self, session: AsyncSession, mobile: str
    ) -> Optional[User]:
        return await self.user_dao.get_by_mobile(session, mobile)

    async def get_user_by_username(
        self, session: AsyncSession, username: str
    ) -> Optional[User]:
        return await self.user_dao.get_by_username(session, username)

    async def get_user_by_id(
        self, session: AsyncSession, user_id: int
    ) -> Optional[User]:
        return await self.user_dao.get_by_id(session, user_id)

    async def change_password(
        self, session: AsyncSession, user_id: int, new_password: str
    ):
        user = await self.user_dao.get_by_id(session, user_id)
        if user:
            user.password = get_password_hash(new_password)
            session.add(user)
            await session.commit()
            return True
        return False

    async def create_superadmin_if_not_exists(
        self,
        session: AsyncSession,
        username: str,
        password: str,
        mobile: str = "0000000000",
    ):
        existing = await self.user_dao.get_by_username(session, username)
        if not existing:
            await self.create_user(
                session,
                mobile=mobile,
                name="Super Admin",
                role=UserRole.SUPERADMIN,
                password=password,
                username=username,
            )
            await session.commit()
            print(f"Superadmin created with username: {username}")
        else:
            print("Superadmin already exists")
