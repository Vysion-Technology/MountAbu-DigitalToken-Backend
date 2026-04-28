from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dbmodels.event import Event
from backend.schemas.request.event import EventCreate, EventUpdate


class EventsDAO:
    async def create_event(self, session: AsyncSession, event: EventCreate, created_by: Optional[int], image_path: Optional[str] = None) -> Event:
        data = event.model_dump()
        db_obj = Event(**data, created_by=created_by, image_path=image_path)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get_event(self, session: AsyncSession, event_id: int) -> Optional[Event]:
        result = await session.execute(select(Event).where(Event.id == event_id))
        return result.scalar_one_or_none()

    async def list_events(self, session: AsyncSession, limit: int = 50, offset: int = 0) -> List[Event]:
        result = await session.execute(select(Event).order_by(Event.date.desc()).limit(limit).offset(offset))
        return result.scalars().all()

    async def update_event(self, session: AsyncSession, event_id: int, data: EventUpdate) -> Optional[Event]:
        update_data = data.model_dump(exclude_unset=True)
        stmt = (
            update(Event).where(Event.id == event_id).values(**update_data).returning(Event)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one_or_none()

    async def delete_event(self, session: AsyncSession, event_id: int) -> bool:
        result = await session.execute(delete(Event).where(Event.id == event_id))
        await session.commit()
        return result.rowcount > 0


def get_events_dao() -> EventsDAO:
    return EventsDAO()
