from typing import Optional
from uuid import uuid4
from fastapi import Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.storage import get_storage_service
from backend.dao.leaders import LeadersDAO, get_leaders_dao
from backend.schemas.request.leader import LeaderCreate, LeaderUpdate
from backend.schemas.response.leader import LeaderResponse, LeadersListResponse


class LeadersService:
    def __init__(self, dao: LeadersDAO):
        self.dao = dao
        self.storage = get_storage_service()

    async def create_leader(self, session: AsyncSession, payload: LeaderCreate, created_by: Optional[int], image: Optional[UploadFile] = None) -> LeaderResponse:
        image_path = None
        if image:
            if not self.storage:
                raise HTTPException(status_code=500, detail="Storage service unavailable")
            uid = uuid4()
            filename = (image.filename or "image").replace(" ", "_")
            object_key = f"leaders/{uid}/{filename}"
            image_path = await self.storage.upload_file(image, object_key)

        db_obj = await self.dao.create_leader(session, payload, created_by, image_path=image_path)
        
        image_url = self.storage.get_file_url(db_obj.image_path) if db_obj.image_path and self.storage else None

        return LeaderResponse(
            id=db_obj.id,
            name=db_obj.name,
            designation=db_obj.designation,
            tenure_start=db_obj.tenure_start,
            tenure_end=db_obj.tenure_end,
            status=db_obj.status,
            image_path=db_obj.image_path,
            image_url=image_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def get_leader(self, session: AsyncSession, leader_id: int) -> LeaderResponse:
        db_obj = await self.dao.get_leader(session, leader_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Leader not found")
        
        image_url = self.storage.get_file_url(db_obj.image_path) if db_obj.image_path and self.storage else None

        return LeaderResponse(
            id=db_obj.id,
            name=db_obj.name,
            designation=db_obj.designation,
            tenure_start=db_obj.tenure_start,
            tenure_end=db_obj.tenure_end,
            status=db_obj.status,
            image_path=db_obj.image_path,
            image_url=image_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def list_leaders(self, session: AsyncSession, limit: int = 50, offset: int = 0) -> LeadersListResponse:
        objs = await self.dao.list_leaders(session, limit=limit, offset=offset)
        items = []
        for d in objs:
            image_url = self.storage.get_file_url(d.image_path) if d.image_path and self.storage else None
            items.append(
                LeaderResponse(
                    id=d.id,
                    name=d.name,
                    designation=d.designation,
                    tenure_start=d.tenure_start,
                    tenure_end=d.tenure_end,
                    status=d.status,
                    image_path=d.image_path,
                    image_url=image_url,
                    created_by=d.created_by,
                    created_at=d.created_at,
                )
            )
        return LeadersListResponse(leaders=items, total=len(items))

    async def update_leader(self, session: AsyncSession, leader_id: int, payload: LeaderUpdate, image: Optional[UploadFile] = None) -> LeaderResponse:
        if image:
            if not self.storage:
                raise HTTPException(status_code=500, detail="Storage service unavailable")
            uid = uuid4()
            filename = (image.filename or "image").replace(" ", "_")
            object_key = f"leaders/{uid}/{filename}"
            payload.image_path = await self.storage.upload_file(image, object_key)

        db_obj = await self.dao.update_leader(session, leader_id, payload)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Leader not found")
        
        image_url = self.storage.get_file_url(db_obj.image_path) if db_obj.image_path and self.storage else None

        return LeaderResponse(
            id=db_obj.id,
            name=db_obj.name,
            designation=db_obj.designation,
            tenure_start=db_obj.tenure_start,
            tenure_end=db_obj.tenure_end,
            status=db_obj.status,
            image_path=db_obj.image_path,
            image_url=image_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def delete_leader(self, session: AsyncSession, leader_id: int) -> bool:
        return await self.dao.delete_leader(session, leader_id)


async def get_leaders_service(dao: LeadersDAO = Depends(get_leaders_dao)) -> LeadersService:
    return LeadersService(dao)