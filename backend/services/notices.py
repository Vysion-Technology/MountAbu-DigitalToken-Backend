from typing import Optional
from uuid import uuid4
from fastapi import Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.storage import get_storage_service
from backend.dao.notices import NoticesDAO, get_notices_dao
from backend.schemas.request.notice import NoticeCreate, NoticeUpdate
from backend.schemas.response.notice import NoticeResponse, NoticesListResponse


class NoticesService:
    def __init__(self, dao: NoticesDAO):
        self.dao = dao
        self.storage = get_storage_service()

    async def create_notice(self, session: AsyncSession, payload: NoticeCreate, created_by: Optional[int], image: Optional[UploadFile] = None, document: Optional[UploadFile] = None) -> NoticeResponse:
        image_path = None
        if image:
            if not self.storage:
                raise HTTPException(status_code=500, detail="Storage service unavailable")
            uid = uuid4()
            filename = (image.filename or "image").replace(" ", "_")
            object_key = f"notices/{uid}/images/{filename}"
            image_path = await self.storage.upload_file(image, object_key)

        document_path = None
        if document:
            if not self.storage:
                raise HTTPException(status_code=500, detail="Storage service unavailable")
            uid = uuid4()
            filename = (document.filename or "doc").replace(" ", "_")
            object_key = f"notices/{uid}/docs/{filename}"
            document_path = await self.storage.upload_file(document, object_key)

        db_obj = await self.dao.create_notice(session, payload, created_by, image_path=image_path, document_path=document_path)
        
        image_url = self.storage.get_file_url(db_obj.image_path) if db_obj.image_path and self.storage else None
        document_url = self.storage.get_file_url(db_obj.document_path) if db_obj.document_path and self.storage else None

        return NoticeResponse(
            id=db_obj.id,
            title=db_obj.title,
            notice_type=db_obj.notice_type,
            published_on=db_obj.published_on,
            valid_till=db_obj.valid_till,
            status=db_obj.status,
            visibility=db_obj.visibility,
            image_path=db_obj.image_path,
            image_url=image_url,
            document_path=db_obj.document_path,
            document_url=document_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def get_notice(self, session: AsyncSession, notice_id: int) -> NoticeResponse:
        db_obj = await self.dao.get_notice(session, notice_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Notice not found")
        
        image_url = self.storage.get_file_url(db_obj.image_path) if db_obj.image_path and self.storage else None
        document_url = self.storage.get_file_url(db_obj.document_path) if db_obj.document_path and self.storage else None

        return NoticeResponse(
            id=db_obj.id,
            title=db_obj.title,
            notice_type=db_obj.notice_type,
            published_on=db_obj.published_on,
            valid_till=db_obj.valid_till,
            status=db_obj.status,
            visibility=db_obj.visibility,
            image_path=db_obj.image_path,
            image_url=image_url,
            document_path=db_obj.document_path,
            document_url=document_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def list_notices(self, session: AsyncSession, limit: int = 50, offset: int = 0) -> NoticesListResponse:
        objs = await self.dao.list_notices(session, limit=limit, offset=offset)
        items = []
        for d in objs:
            image_url = self.storage.get_file_url(d.image_path) if d.image_path and self.storage else None
            document_url = self.storage.get_file_url(d.document_path) if d.document_path and self.storage else None
            items.append(
                NoticeResponse(
                    id=d.id,
                    title=d.title,
                    notice_type=d.notice_type,
                    published_on=d.published_on,
                    valid_till=d.valid_till,
                    status=d.status,
                    visibility=d.visibility,
                    image_path=d.image_path,
                    image_url=image_url,
                    document_path=d.document_path,
                    document_url=document_url,
                    created_by=d.created_by,
                    created_at=d.created_at,
                )
            )
        return NoticesListResponse(notices=items, total=len(items))

    async def update_notice(self, session: AsyncSession, notice_id: int, payload: NoticeUpdate, image: Optional[UploadFile] = None, document: Optional[UploadFile] = None) -> NoticeResponse:
        if image:
            if not self.storage:
                raise HTTPException(status_code=500, detail="Storage service unavailable")
            uid = uuid4()
            filename = (image.filename or "image").replace(" ", "_")
            object_key = f"notices/{uid}/images/{filename}"
            payload.image_path = await self.storage.upload_file(image, object_key)

        if document:
            if not self.storage:
                raise HTTPException(status_code=500, detail="Storage service unavailable")
            uid = uuid4()
            filename = (document.filename or "doc").replace(" ", "_")
            object_key = f"notices/{uid}/docs/{filename}"
            payload.document_path = await self.storage.upload_file(document, object_key)

        db_obj = await self.dao.update_notice(session, notice_id, payload)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Notice not found")
        
        image_url = self.storage.get_file_url(db_obj.image_path) if db_obj.image_path and self.storage else None
        document_url = self.storage.get_file_url(db_obj.document_path) if db_obj.document_path and self.storage else None

        return NoticeResponse(
            id=db_obj.id,
            title=db_obj.title,
            notice_type=db_obj.notice_type,
            published_on=db_obj.published_on,
            valid_till=db_obj.valid_till,
            status=db_obj.status,
            visibility=db_obj.visibility,
            image_path=db_obj.image_path,
            image_url=image_url,
            document_path=db_obj.document_path,
            document_url=document_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def delete_notice(self, session: AsyncSession, notice_id: int) -> bool:
        return await self.dao.delete_notice(session, notice_id)


async def get_notices_service(dao: NoticesDAO = Depends(get_notices_dao)) -> NoticesService:
    return NoticesService(dao)
