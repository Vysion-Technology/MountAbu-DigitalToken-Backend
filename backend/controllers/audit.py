from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.middlewares.auth import get_audit_viewer, UserDetails
from backend.services.audit import AuditService
from backend.schemas.audit import AuditLogListResponse

router = APIRouter(prefix="/audit", tags=["Audit Log"])
audit_service = AuditService()


@router.get("", response_model=AuditLogListResponse)
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_audit_viewer),
):
    logs, total = await audit_service.get_logs(db, skip, limit)
    return {"total": total, "logs": logs}
