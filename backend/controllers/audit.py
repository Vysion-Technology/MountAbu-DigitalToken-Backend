from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.middlewares.auth import get_audit_viewer, UserDetails
from backend.services.audit import AuditService
from backend.schemas.audit import AuditLogListResponse
from backend.meta.audit import AuditAction

router = APIRouter(prefix="/audit", tags=["Audit Log"])
audit_service = AuditService()


@router.get("", response_model=AuditLogListResponse)
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    entity_type: Optional[str] = Query(
        None, description="Filter by entity type (e.g. APPLICATION)"
    ),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_audit_viewer),
):
    logs, total = await audit_service.get_logs(
        db, skip, limit, user_id, action, entity_type, start_date, end_date
    )
    return {"total": total, "logs": logs}
