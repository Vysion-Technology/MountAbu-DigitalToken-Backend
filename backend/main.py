from contextlib import asynccontextmanager
import subprocess
from fastapi import FastAPI
from backend.controllers.auth import router as auth_router
from backend.controllers.application import router as app_router
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup
    print("Running migrations...")
    try:
        # Assumes running from project root (/app)
        subprocess.run(
            ["alembic", "-c", "backend/alembic.ini", "upgrade", "head"], check=True
        )
        print("Migrations completed successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
    yield


app = FastAPI(title="Mount Abu E-Token System", lifespan=lifespan)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(app_router, prefix="/api", tags=["Applications"])


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
