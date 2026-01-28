from minio import Minio
from backend.config import settings
from fastapi import UploadFile
import io

class StorageService:
    def __init__(self):
        self.client = Minio(
            f"{settings.MINIO_HOST}:9000",
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False
        )
        self.bucket_name = "documents"
        self._ensure_bucket()

    def _ensure_bucket(self):
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)
    
    async def upload_file(self, file: UploadFile, object_name: str) -> str:
        content = await file.read()
        self.client.put_object(
            self.bucket_name,
            object_name,
            io.BytesIO(content),
            length=len(content),
            content_type=file.content_type
        )
        await file.seek(0) # Reset pointer if needed elsewhere
        return f"{self.bucket_name}/{object_name}"

    def get_file_url(self, object_name: str) -> str:
        # Generate presigned URL valid for 1 hour
        return self.client.presigned_get_object(self.bucket_name, object_name)

_storage_service = None

def get_storage_service():
    global _storage_service
    if _storage_service is None:
        try:
            _storage_service = StorageService()
        except Exception as e:
            print(f"Failed to init MinIO: {e}")
            return None
    return _storage_service
