import asyncio
import sys
import os

sys.path.append(os.getcwd())


async def fix_enum():
    from backend.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    print(f"Connecting to {settings.database_url}")
    engine = create_async_engine(
        settings.database_url, echo=True, isolation_level="AUTOCOMMIT"
    )

    async with engine.connect() as conn:
        print("Adding WITHDRAWN to applicationstatus...")
        try:
            await conn.execute(
                text("ALTER TYPE applicationstatus ADD VALUE 'WITHDRAWN'")
            )
            print("SUCCESS: applicationstatus updated")
        except Exception as e:
            print(f"ERROR applicationstatus: {e}")

        print("Adding WITHDRAWN to complaintstatus...")
        try:
            await conn.execute(text("ALTER TYPE complaintstatus ADD VALUE 'WITHDRAWN'"))
            print("SUCCESS: complaintstatus updated")
        except Exception as e:
            print(f"ERROR complaintstatus: {e}")

        print("Adding WITHDRAW to workflowaction...")
        try:
            await conn.execute(text("ALTER TYPE workflowaction ADD VALUE 'WITHDRAW'"))
            print("SUCCESS: workflowaction updated")
        except Exception as e:
            print(f"ERROR workflowaction: {e}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_enum())
