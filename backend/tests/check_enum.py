import asyncio
import sys
import os

sys.path.append(os.getcwd())


async def check_enum():
    from backend.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    print(f"Connecting to {settings.database_url}")
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.connect() as conn:
        print("--- APPLICATION STATUS ---")
        result = await conn.execute(
            text("SELECT unnest(enum_range(null::applicationstatus))")
        )
        for row in result:
            print(row[0])

        print("--- COMPLAINT STATUS ---")
        result = await conn.execute(
            text("SELECT unnest(enum_range(null::complaintstatus))")
        )
        for row in result:
            print(row[0])


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_enum())
