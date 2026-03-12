from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.middlewares.auth import get_admin_or_nodal
from backend.schemas.base.auth import UserDetails
from backend.services.events import EventsService, get_events_service
from backend.schemas.request.event import EventCreate, EventUpdate
from backend.schemas.response.event import EventResponse, EventsListResponse
from backend.schemas.response.meta import SuccessResponse
from backend.services.audit import AuditService
from backend.meta.audit import AuditAction

router = APIRouter()
audit_service = AuditService()


@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(
    payload: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: EventsService = Depends(get_events_service),
):
    response = await service.create_event(db, payload, current_user.user_id)
    await audit_service.log(
        db,
        "EVENT",
        AuditAction.CREATED,
        current_user.user_id,
        new_state=response.model_dump(mode="json") if hasattr(response, "model_dump") else None,
    )
    await db.commit()
    return response


@router.get("/events", response_model=EventsListResponse)
async def list_events(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    service: EventsService = Depends(get_events_service),
):
    return await service.list_events(db, limit=limit, offset=offset)


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    service: EventsService = Depends(get_events_service),
):
    return await service.get_event(db, event_id)


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    payload: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: EventsService = Depends(get_events_service),
):
    response = await service.update_event(db, event_id, payload)
    await audit_service.log(
        db,
        "EVENT",
        AuditAction.CHANGED,
        current_user.user_id,
        new_state=response.model_dump(mode="json") if hasattr(response, "model_dump") else None,
    )
    await db.commit()
    return response


@router.delete("/events/{event_id}", response_model=SuccessResponse)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: EventsService = Depends(get_events_service),
):
    ok = await service.delete_event(db, event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")

    await audit_service.log(
        db,
        "EVENT",
        AuditAction.CHANGED,
        current_user.user_id,
        new_state={"id": event_id, "action": "deleted"},
    )
    await db.commit()
    return SuccessResponse(message="Event deleted successfully")
