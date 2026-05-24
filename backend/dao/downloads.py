from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dbmodels.download import Download
from backend.schemas.request.download import DownloadCreate, DownloadUpdate
from backend.meta import DownloadStatus


class DownloadsDAO:
    async def create_download(self, session: AsyncSession, download: DownloadCreate, uploaded_by: Optional[int], file_path: str) -> Download:
        data = download.model_dump()
        db_obj = Download(**data, file_path=file_path, uploaded_by=uploaded_by)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get_download(self, session: AsyncSession, download_id: int, active_only: bool = False) -> Optional[Download]:
        stmt = select(Download).where(Download.id == download_id)
        if active_only:
            stmt = stmt.where(Download.status == DownloadStatus.ACTIVE)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_downloads(self, session: AsyncSession, limit: int = 50, offset: int = 0, active_only: bool = False) -> List[Download]:
        stmt = select(Download).order_by(Download.uploaded_on.desc()).limit(limit).offset(offset)
        if active_only:
            stmt = stmt.where(Download.status == DownloadStatus.ACTIVE)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update_download(self, session: AsyncSession, download_id: int, data: DownloadUpdate) -> Optional[Download]:
        update_data = data.model_dump(exclude_unset=True)
        stmt = (
            update(Download).where(Download.id == download_id).values(**update_data).returning(Download)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one_or_none()

    async def delete_download(self, session: AsyncSession, download_id: int) -> bool:
        result = await session.execute(delete(Download).where(Download.id == download_id))
        await session.commit()
        return result.rowcount > 0


def get_downloads_dao() -> DownloadsDAO:
    return DownloadsDAO()
