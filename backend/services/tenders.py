from typing import Optional
from uuid import uuid4
from fastapi import Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.storage import get_storage_service
from backend.dao.tenders import TendersDAO, get_tenders_dao
from backend.schemas.request.tender import TenderCreate, TenderUpdate
from backend.schemas.response.tender import TenderResponse, TendersListResponse


class TendersService:
    def __init__(self, dao: TendersDAO):
        self.dao = dao
        self.storage = get_storage_service()

    async def create_tender(self, session: AsyncSession, payload: TenderCreate, created_by: Optional[int], document: Optional[UploadFile] = None) -> TenderResponse:
        document_path = None
        if document:
            if not self.storage:
                raise HTTPException(status_code=500, detail="Storage service unavailable")
            uid = uuid4()
            filename = (document.filename or "file").replace(" ", "_")
            object_key = f"tenders/{uid}/{filename}"
            document_path = await self.storage.upload_file(document, object_key)

        db_obj = await self.dao.create_tender(session, payload, created_by, document_path=document_path)
        
        doc_url = self.storage.get_file_url(db_obj.document_path) if db_obj.document_path and self.storage else None

        return TenderResponse(
            id=db_obj.id,
            title=db_obj.title,
            tender_type=db_obj.tender_type,
            department_id=db_obj.department_id,
            amount=float(db_obj.amount) if db_obj.amount is not None else None,
            published_on=db_obj.published_on,
            submission_deadline=db_obj.submission_deadline,
            status=db_obj.status,
            document_path=db_obj.document_path,
            document_url=doc_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def get_tender(self, session: AsyncSession, tender_id: int) -> TenderResponse:
        db_obj = await self.dao.get_tender(session, tender_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Tender not found")
        
        doc_url = self.storage.get_file_url(db_obj.document_path) if db_obj.document_path and self.storage else None

        return TenderResponse(
            id=db_obj.id,
            title=db_obj.title,
            tender_type=db_obj.tender_type,
            department_id=db_obj.department_id,
            amount=float(db_obj.amount) if db_obj.amount is not None else None,
            published_on=db_obj.published_on,
            submission_deadline=db_obj.submission_deadline,
            status=db_obj.status,
            document_path=db_obj.document_path,
            document_url=doc_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def list_tenders(self, session: AsyncSession, limit: int = 50, offset: int = 0) -> TendersListResponse:
        objs = await self.dao.list_tenders(session, limit=limit, offset=offset)
        items = []
        for d in objs:
            doc_url = self.storage.get_file_url(d.document_path) if d.document_path and self.storage else None
            items.append(
                TenderResponse(
                    id=d.id,
                    title=d.title,
                    tender_type=d.tender_type,
                    department_id=d.department_id,
                    amount=float(d.amount) if d.amount is not None else None,
                    published_on=d.published_on,
                    submission_deadline=d.submission_deadline,
                    status=d.status,
                    document_path=d.document_path,
                    document_url=doc_url,
                    created_by=d.created_by,
                    created_at=d.created_at,
                )
            )
        return TendersListResponse(tenders=items, total=len(items))

    async def update_tender(self, session: AsyncSession, tender_id: int, payload: TenderUpdate, document: Optional[UploadFile] = None) -> TenderResponse:
        if document:
            if not self.storage:
                raise HTTPException(status_code=500, detail="Storage service unavailable")
            uid = uuid4()
            filename = (document.filename or "file").replace(" ", "_")
            object_key = f"tenders/{uid}/{filename}"
            payload.document_path = await self.storage.upload_file(document, object_key)

        db_obj = await self.dao.update_tender(session, tender_id, payload)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Tender not found")
        
        doc_url = self.storage.get_file_url(db_obj.document_path) if db_obj.document_path and self.storage else None

        return TenderResponse(
            id=db_obj.id,
            title=db_obj.title,
            tender_type=db_obj.tender_type,
            department_id=db_obj.department_id,
            amount=float(db_obj.amount) if db_obj.amount is not None else None,
            published_on=db_obj.published_on,
            submission_deadline=db_obj.submission_deadline,
            status=db_obj.status,
            document_path=db_obj.document_path,
            document_url=doc_url,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
        )

    async def delete_tender(self, session: AsyncSession, tender_id: int) -> bool:
        return await self.dao.delete_tender(session, tender_id)


async def get_tenders_service(dao: TendersDAO = Depends(get_tenders_dao)) -> TendersService:
    return TendersService(dao)