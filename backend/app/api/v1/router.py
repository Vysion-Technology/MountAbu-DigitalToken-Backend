"""API v1 router aggregating all endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, applications, tokens, blacklist, reports

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(
    applications.router, prefix="/applications", tags=["Applications"]
)
api_router.include_router(tokens.router, prefix="/tokens", tags=["Tokens"])
api_router.include_router(blacklist.router, prefix="/blacklist", tags=["Blacklist"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
