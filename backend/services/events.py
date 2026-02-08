from typing import Optional
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dao.events import EventsDAO, get_events_dao
from backend.schemas.request.event import EventCreate, EventUpdate
from backend.schemas.response.event import EventResponse, EventsListResponse


class EventsService:
    def __init__(self, dao: EventsDAO):
        self.dao = dao

    async def create_event(self, session: AsyncSession, payload: EventCreate, created_by: Optional[int]) -> EventResponse:
        db_obj = await self.dao.create_event(session, payload, created_by)
        return EventResponse(
            id=db_obj.id,
            title=db_obj.title,
            event_type=db_obj.event_type,
            date=db_obj.date,
            venue=db_obj.venue,
            status=db_obj.status,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def get_event(self, session: AsyncSession, event_id: int) -> EventResponse:
        db_obj = await self.dao.get_event(session, event_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Event not found")
        return EventResponse(
            id=db_obj.id,
            title=db_obj.title,
            event_type=db_obj.event_type,
            date=db_obj.date,
            venue=db_obj.venue,
            status=db_obj.status,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def list_events(self, session: AsyncSession, limit: int = 50, offset: int = 0) -> EventsListResponse:
        objs = await self.dao.list_events(session, limit=limit, offset=offset)
        items = [
            EventResponse(
                id=d.id,
                title=d.title,
                event_type=d.event_type,
                date=d.date,
                venue=d.venue,
                status=d.status,
                created_by=d.created_by,
                created_at=d.created_at,
            )
            for d in objs
        ]
        return EventsListResponse(events=items, total=len(items))

    async def update_event(self, session: AsyncSession, event_id: int, payload: EventUpdate) -> EventResponse:
        db_obj = await self.dao.update_event(session, event_id, payload)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Event not found")
        return EventResponse(
            id=db_obj.id,
            title=db_obj.title,
            event_type=db_obj.event_type,
            date=db_obj.date,
            venue=db_obj.venue,
            status=db_obj.status,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def delete_event(self, session: AsyncSession, event_id: int) -> bool:
        return await self.dao.delete_event(session, event_id)


async def get_events_service(dao: EventsDAO = Depends(get_events_dao)) -> EventsService:
    return EventsService(dao)