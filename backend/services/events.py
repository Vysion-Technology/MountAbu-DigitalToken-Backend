from typing import Optional
from uuid import uuid4
from fastapi import Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.storage import get_storage_service
from backend.dao.events import EventsDAO, get_events_dao
from backend.schemas.request.event import EventCreate, EventUpdate
from backend.schemas.response.event import EventResponse, EventsListResponse
from backend.meta import UserRole
from backend.schemas.base.auth import UserDetails


class EventsService:
    def __init__(self, dao: EventsDAO):
        self.dao = dao
        self.storage = get_storage_service()

    async def create_event(self, session: AsyncSession, payload: EventCreate, created_by: Optional[int], image: Optional[UploadFile] = None) -> EventResponse:
        image_path = None
        if image:
            if not self.storage:
                raise HTTPException(status_code=500, detail="Storage service unavailable")
            uid = uuid4()
            filename = (image.filename or "image").replace(" ", "_")
            object_key = f"events/{uid}/{filename}"
            image_path = await self.storage.upload_file(image, object_key)

        db_obj = await self.dao.create_event(session, payload, created_by, image_path=image_path)
        
        image_url = self.storage.get_file_url(db_obj.image_path) if db_obj.image_path and self.storage else None

        return EventResponse(
            id=db_obj.id,
            title=db_obj.title,
            event_type=db_obj.event_type,
            date=db_obj.date,
            venue=db_obj.venue,
            description=db_obj.description,
            status=db_obj.status,
            image_path=db_obj.image_path,
            image_url=image_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def get_event(self, session: AsyncSession, event_id: int, user: Optional[UserDetails] = None) -> EventResponse:
        active_only = True if not user or user.role != UserRole.SUPERADMIN else False
        db_obj = await self.dao.get_event(session, event_id, active_only=active_only)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Event not found")
        
        image_url = self.storage.get_file_url(db_obj.image_path) if db_obj.image_path and self.storage else None

        return EventResponse(
            id=db_obj.id,
            title=db_obj.title,
            event_type=db_obj.event_type,
            date=db_obj.date,
            venue=db_obj.venue,
            description=db_obj.description,
            status=db_obj.status,
            image_path=db_obj.image_path,
            image_url=image_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def list_events(self, session: AsyncSession, limit: int = 50, offset: int = 0, user: Optional[UserDetails] = None) -> EventsListResponse:
        active_only = True if not user or user.role != UserRole.SUPERADMIN else False
        objs = await self.dao.list_events(session, limit=limit, offset=offset, active_only=active_only)
        items = []
        for d in objs:
            image_url = self.storage.get_file_url(d.image_path) if d.image_path and self.storage else None
            items.append(
                EventResponse(
                    id=d.id,
                    title=d.title,
                    event_type=d.event_type,
                    date=d.date,
                    venue=d.venue,
                    description=d.description,
                    status=d.status,
                    image_path=d.image_path,
                    image_url=image_url,
                    created_by=d.created_by,
                    created_at=d.created_at,
                )
            )
        return EventsListResponse(events=items, total=len(items))

    async def update_event(self, session: AsyncSession, event_id: int, payload: EventUpdate, image: Optional[UploadFile] = None) -> EventResponse:
        if image:
            if not self.storage:
                raise HTTPException(status_code=500, detail="Storage service unavailable")
            uid = uuid4()
            filename = (image.filename or "image").replace(" ", "_")
            object_key = f"events/{uid}/{filename}"
            payload.image_path = await self.storage.upload_file(image, object_key)

        db_obj = await self.dao.update_event(session, event_id, payload)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Event not found")
        
        image_url = self.storage.get_file_url(db_obj.image_path) if db_obj.image_path and self.storage else None

        return EventResponse(
            id=db_obj.id,
            title=db_obj.title,
            event_type=db_obj.event_type,
            date=db_obj.date,
            venue=db_obj.venue,
            description=db_obj.description,
            status=db_obj.status,
            image_path=db_obj.image_path,
            image_url=image_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def delete_event(self, session: AsyncSession, event_id: int) -> bool:
        return await self.dao.delete_event(session, event_id)


async def get_events_service(dao: EventsDAO = Depends(get_events_dao)) -> EventsService:
    return EventsService(dao)