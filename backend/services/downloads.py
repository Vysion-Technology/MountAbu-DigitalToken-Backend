from uuid import uuid4
from typing import Optional
from fastapi import UploadFile, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.storage import get_storage_service
from backend.dao.downloads import DownloadsDAO, get_downloads_dao
from backend.schemas.request.download import DownloadCreate, DownloadUpdate
from backend.schemas.response.download import DownloadResponse, DownloadsListResponse
from backend.meta import UserRole
from backend.schemas.base.auth import UserDetails


class DownloadsService:
    def __init__(self, dao: DownloadsDAO):
        self.dao = dao
        self.storage = get_storage_service()

    async def create_download(self, session: AsyncSession, payload: DownloadCreate, file: UploadFile, user_id: Optional[int]) -> DownloadResponse:
        if not self.storage:
            raise HTTPException(status_code=500, detail="Storage service unavailable")

        # Create an S3 key: downloads/{uuid}/{filename}
        uid = uuid4()
        filename = (file.filename or "file").replace(" ", "_")
        object_key = f"downloads/{uid}/{filename}"

        # Upload file
        path = await self.storage.upload_file(file, object_key)

        db_obj = await self.dao.create_download(session, payload, uploaded_by=user_id, file_path=path)

        file_url = self.storage.get_file_url(path)

        return DownloadResponse(
            id=db_obj.id,
            document_title=db_obj.document_title,
            document_type=db_obj.document_type,
            department_id=db_obj.department_id,
            description=db_obj.description,
            file_path=db_obj.file_path,
            file_url=file_url,
            status=db_obj.status,
            uploaded_by=db_obj.uploaded_by,
            uploaded_on=db_obj.uploaded_on,
        )

    async def get_download(self, session: AsyncSession, download_id: int, user: Optional[UserDetails] = None) -> DownloadResponse:
        active_only = True if not user or user.role != UserRole.SUPERADMIN else False
        db_obj = await self.dao.get_download(session, download_id, active_only=active_only)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Download not found")
        file_url = self.storage.get_file_url(db_obj.file_path) if self.storage else None
        return DownloadResponse(
            id=db_obj.id,
            document_title=db_obj.document_title,
            document_type=db_obj.document_type,
            department_id=db_obj.department_id,
            description=db_obj.description,
            file_path=db_obj.file_path,
            file_url=file_url,
            status=db_obj.status,
            uploaded_by=db_obj.uploaded_by,
            uploaded_on=db_obj.uploaded_on,
        )

    async def list_downloads(self, session: AsyncSession, limit: int = 50, offset: int = 0, user: Optional[UserDetails] = None) -> DownloadsListResponse:
        active_only = True if not user or user.role != UserRole.SUPERADMIN else False
        objs = await self.dao.list_downloads(session, limit=limit, offset=offset, active_only=active_only)
        items = []
        for d in objs:
            file_url = self.storage.get_file_url(d.file_path) if self.storage else None
            items.append(
                DownloadResponse(
                    id=d.id,
                    document_title=d.document_title,
                    document_type=d.document_type,
                    department_id=d.department_id,
                    description=d.description,
                    file_path=d.file_path,
                    file_url=file_url,
                    status=d.status,
                    uploaded_by=d.uploaded_by,
                    uploaded_on=d.uploaded_on,
                )
            )
        return DownloadsListResponse(downloads=items, total=len(items))

    async def update_download(self, session: AsyncSession, download_id: int, payload: DownloadUpdate) -> DownloadResponse:
        db_obj = await self.dao.update_download(session, download_id, payload)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Download not found")
        file_url = self.storage.get_file_url(db_obj.file_path) if self.storage else None
        return DownloadResponse(
            id=db_obj.id,
            document_title=db_obj.document_title,
            document_type=db_obj.document_type,
            department_id=db_obj.department_id,
            description=db_obj.description,
            file_path=db_obj.file_path,
            file_url=file_url,
            status=db_obj.status,
            uploaded_by=db_obj.uploaded_by,
            uploaded_on=db_obj.uploaded_on,
        )

    async def delete_download(self, session: AsyncSession, download_id: int) -> bool:
        # Remove file from storage (best-effort), then delete DB record
        db_obj = await self.dao.get_download(session, download_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Download not found")

        # Attempt to delete from storage if available
        if self.storage and db_obj.file_path:
            try:
                self.storage.delete_file(db_obj.file_path)
            except Exception as e:
                # Log and continue — do not block DB deletion on storage failure
                print(f"Failed to delete file from storage for download {download_id}: {e}")

        return await self.dao.delete_download(session, download_id)


async def get_downloads_service(dao: DownloadsDAO = Depends(get_downloads_dao)) -> DownloadsService:
    return DownloadsService(dao)
