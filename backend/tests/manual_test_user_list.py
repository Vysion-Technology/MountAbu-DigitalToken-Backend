import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Adjust these imports based on your project structure
# Assuming running from the root as: python -m backend.tests.manual_test_user_list
from backend.config import settings
from backend.dao.user import UserDAO
from backend.dbmodels.user import User
from backend.meta import UserRole

# Create a clean engine/session for testing
engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def test_dao_filtering():
    async with AsyncSessionLocal() as session:
        dao = UserDAO()

        # 1. Create dummy users for testing
        print("Creating dummy users...")
        citizen = await dao.create_user(
            session, mobile="9999999990", role=UserRole.CITIZEN, name="TestCitizen"
        )
        official = await dao.create_user(
            session,
            mobile="9999999991",
            role=UserRole.NODAL_OFFICER,
            name="TestOfficial",
        )

        # 2. Test fetching CITIZENS
        print("Fetching CITIZENS...")
        citizens = await dao.get_users_filtered(session, is_citizen=True)
        print(f"Found {len(citizens)} citizens.")
        for u in citizens:
            if u.role != UserRole.CITIZEN:
                print(f"ERROR: Found non-citizen {u.role} in citizen list!")
            else:
                pass
                # print(f"  - {u.name} ({u.role})")

        # 3. Test fetching OFFICIALS
        print("Fetching OFFICIALS...")
        officials = await dao.get_users_filtered(session, is_citizen=False)
        print(f"Found {len(officials)} officials.")
        for u in officials:
            if u.role == UserRole.CITIZEN:
                print(f"ERROR: Found citizen {u.role} in official list!")
            else:
                pass
                # print(f"  - {u.name} ({u.role})")

        # Cleanup (optional, dependent on DB persistence policy for tests)
        # For now, we leave them or rollback if we wrapped in a transaction check.
        # But create_user commits? No, create_user in DAO flushes but doesn't commit except create_otp.
        # Wait, create_user in DAO: `await session.flush()`. It relies on caller to commit.
        # So if we don't commit here, they won't be saved?
        # Actually `UserDAO.create_user` implementation:
        # `session.add(user); await session.flush()`
        # So they are in the session.
        # But `get_users_filtered` runs a select. If we haven't committed, will select see them?
        # Yes, within the same transaction/session.

        # Let's verify our specific created users are finding their way back.
        found_citizen = any(u.mobile == "9999999990" for u in citizens)
        found_official = any(u.mobile == "9999999991" for u in officials)

        print(f"Test Citizen found: {found_citizen}")
        print(f"Test Official found: {found_official}")

        if found_citizen and found_official:
            print("SUCCESS: DAO Filtering works as expected.")
        else:
            print("FAILURE: Did not find created test users.")

        await session.rollback()  # Clean up


if __name__ == "__main__":
    asyncio.run(test_dao_filtering())
