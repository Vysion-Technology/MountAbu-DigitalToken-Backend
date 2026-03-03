from contextlib import asynccontextmanager
import subprocess
from fastapi import FastAPI
import uvicorn

from backend.controllers.auth import router as auth_router
from backend.controllers.application import router as app_router
from backend.controllers.superadmin import router as superadmin_router
from backend.controllers.master import router as master_router
from backend.controllers.media import router as media_router
from backend.controllers.complaint import router as complaint_router
from backend.controllers.city_profile import router as city_profile_router
from backend.controllers.downloads import router as downloads_router
from backend.controllers.notices import router as notices_router
from backend.controllers.tenders import router as tenders_router
from backend.controllers.events import router as events_router
from backend.controllers.leaders import router as leaders_router
from backend.controllers.naka import router as naka_router

from backend.controllers.dashboard import router as dashboard_router
from backend.controllers.user_management import router as user_management_router
from backend.controllers.audit import router as audit_router
from backend.controllers.contact_diary import router as contact_diary_router


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
app.include_router(superadmin_router, prefix="/superadmin", tags=["SuperAdmin"])
app.include_router(app_router, prefix="/api", tags=["Applications"])
app.include_router(master_router, prefix="/api", tags=["Master Data"])
app.include_router(media_router, prefix="/api", tags=["Media"])
app.include_router(downloads_router, prefix="/api", tags=["Downloads"])
app.include_router(notices_router, prefix="/api", tags=["Notices"])
app.include_router(tenders_router, prefix="/api", tags=["Tenders"])
app.include_router(events_router, prefix="/api", tags=["Events"])
app.include_router(leaders_router, prefix="/api", tags=["Leaders"])
app.include_router(complaint_router, prefix="/api", tags=["Complaints"])
app.include_router(naka_router, prefix="/api", tags=["Naka"])
app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
app.include_router(city_profile_router, prefix="/api", tags=["City Profile"])
app.include_router(user_management_router, prefix="/api", tags=["User Management"])
app.include_router(audit_router, prefix="/api", tags=["Audit Log"])
app.include_router(
    contact_diary_router, prefix="/api/contact-diary", tags=["Contact Diary"]
)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
