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

    def upload_bytes(self, object_name: str, data: bytes, content_type: str) -> str:
        """Upload raw bytes to MinIO. Returns the stored path."""
        self.client.put_object(
            self.bucket_name,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return f"{self.bucket_name}/{object_name}"

    def get_file_url(self, object_name: str) -> str:
        # Generate presigned GET URL valid for 1 hour
        return self.client.presigned_get_object(self.bucket_name, object_name)

    def get_presigned_upload_url(self, object_name: str) -> str:
        # Generate presigned PUT URL valid for 10 minutes
        from datetime import timedelta

        return self.client.presigned_put_object(
            self.bucket_name, object_name, expires=timedelta(minutes=10)
        )

    def delete_file(self, object_path: str) -> None:
        """Delete object from storage. object_path may be either an object name or a stored path like 'bucket/object'."""
        try:
            # Normalize to object_name (strip bucket if present)
            if object_path.startswith(f"{self.bucket_name}/"):
                object_name = object_path.split("/", 1)[1]
            else:
                object_name = object_path

            self.client.remove_object(self.bucket_name, object_name)
        except Exception as e:
            # Log and re-raise so callers can handle or fail gracefully
            print(f"Warning: failed to delete object {object_path}: {e}")
            raise


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
