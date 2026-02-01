import asyncio
import asyncpg
import os

# Override host for local execution
DB_HOST = os.getenv("DATABASE_HOST", "localhost")
DB_USER = "etoken_user"
DB_PASS = "etoken_secure_password_123"
DB_NAME = "mountabu_etoken"
DB_PORT = 5432

VALUES_TO_ADD = [
    "AADHAAR",
    "APPLICANT_PHOTO",
    "OWNERSHIP_DOCUMENTS",
    "PROPERTY_PHOTOS",
    "SUPPORTING_DOCUMENTS"
]

async def main():
    dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    print(f"Connecting to {dsn}")
    conn = await asyncpg.connect(dsn)
    try:
        for val in VALUES_TO_ADD:
            print(f"Adding value {val}...")
            try:
                await conn.execute(f"ALTER TYPE applicationdocumenttype ADD VALUE '{val}';")
                print(f"Added {val}")
            except asyncpg.exceptions.DuplicateObjectError:
                print(f"Value {val} already exists")
            except Exception as e:
                # Postgres throws error if we try to add value inside transaction block sometimes, 
                # but asyncpg.connect gives autocommit connection by default usually? 
                # Actually ALTER TYPE cannot run inside a transaction block. 
                # asyncpg connection is not in transaction unless we start one.
                print(f"Error adding {val}: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
