from minio import Minio
from backend.config import settings
from fastapi import UploadFile
import hmac
import hashlib
import io
import time
import urllib.parse
import magic
import os

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
    
    async def validate_file(
        self, 
        file: UploadFile, 
        allowed_mime_types: list[str] = ["image/jpeg", "image/png", "image/jpg", "application/pdf"],
        max_size_mb: int = 10
    ):
        """
        Validates a file based on:
        1. Filename sanitization (Null bytes, Double extensions).
        2. Secure size enforcement (Seeking to end).
        3. Magic byte inspection (MIME validation).
        """
        filename = file.filename or ""
        
        # 1. Filename Sanitization
        # Check for Null Byte Injection
        if "%00" in filename or "\x00" in filename:
            raise ValueError("Invalid filename: Null byte injection detected.")
        
        # Check for Double Extensions
        if filename.count('.') > 1:
            raise ValueError("Invalid filename: Double extensions are not allowed.")
        
        # 2. Secure Size Enforcement
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        await file.seek(0)
        
        if file_size > max_size_mb * 1024 * 1024:
            raise ValueError(f"File size exceeds the limit of {max_size_mb}MB.")
        
        # 3. Magic Byte Inspection (MIME Validation)
        # Read the first 2048 bytes for magic byte inspection
        header = await file.read(2048)
        await file.seek(0)
        
        mime_type = magic.from_buffer(header, mime=True)
        
        # 4. Extension-Content Integrity Check
        ext = os.path.splitext(filename)[1].lower()
        
        # This map defines which extensions are allowed and which MIME types they must contain.
        # If an extension is not in this map, it is rejected entirely.
        mime_map = {
            ".pdf": ["application/pdf"],
            ".jpg": ["image/jpeg"],
            ".jpeg": ["image/jpeg"],
            ".png": ["image/png"],
            # Add more recognized extensions here as needed
        }
        
        # Reject unknown/unsupported extensions
        if ext not in mime_map:
            raise ValueError(f"Unsupported or dangerous file extension: {ext}")
        
        # Reject if the content does not match the extension
        if mime_type not in mime_map[ext]:
            raise ValueError(f"Content mismatch: File extension is {ext} but detected content is {mime_type}")

        # Normalize jpg to image/jpeg if needed (magic usually returns image/jpeg for both)
        if mime_type not in allowed_mime_types:
            raise ValueError(f"Invalid file type: {mime_type}. Allowed types: {', '.join(allowed_mime_types)}")
            
        # Store the detected mime type on the file object for later use
        setattr(file, "custom_mime_type", mime_type)
        
        return mime_type, file_size

    async def upload_file(self, file: UploadFile, object_name: str, validate: bool = True, **kwargs) -> str:
        if validate:
            content_type, _ = await self.validate_file(file, **kwargs)
        else:
            content_type = file.content_type or "application/octet-stream"

        content = await file.read()
        self.client.put_object(
            self.bucket_name,
            object_name,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type
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

    def get_file_url(self, object_name: str, expires_hours: int = 3) -> str:
        """Generate a signed backend proxy URL valid for *expires_hours* hours.

        The URL points to the backend download-proxy endpoint so that
        clients never talk to MinIO directly.
        """
        return generate_signed_file_url(object_name, expires_hours)

    def get_file_stream(self, object_name: str):
        """Return the raw MinIO response object (streaming) for *object_name*.

        Callers are responsible for closing the response when done.
        """
        # Normalise: strip bucket prefix if the stored path includes it
        if object_name.startswith(f"{self.bucket_name}/"):
            object_name = object_name.split("/", 1)[1]
        return self.client.get_object(self.bucket_name, object_name)

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


# ---------------------------------------------------------------------------
# Standalone signed-URL helpers (usable without a StorageService instance)
# ---------------------------------------------------------------------------

def _sign_download_token(object_path: str, expires_at: int) -> str:
    """Create an HMAC-SHA256 token binding *object_path* to *expires_at*."""
    message = f"{object_path}:{expires_at}"
    return hmac.new(
        settings.SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_signed_file_url(object_path: str, expires_hours: int = 3) -> str:
    """Return a backend-proxied download URL with a signed token.

    This can be called from anywhere (services, Pydantic validators, etc.)
    without needing a StorageService instance.
    """
    # Normalise stored paths that may include the bucket prefix
    clean_path = object_path
    if clean_path.startswith("documents/"):
        clean_path = clean_path.split("/", 1)[1]

    expires_at = int(time.time()) + expires_hours * 3600
    token = _sign_download_token(clean_path, expires_at)
    encoded_path = urllib.parse.quote(clean_path, safe="/")
    return (
        f"{settings.BACKEND_BASE_URL}/api/media/file/"
        f"{encoded_path}?token={token}&expires={expires_at}"
    )


def verify_download_token(object_path: str, token: str, expires: int) -> bool:
    """Verify that *token* is valid for *object_path* and has not expired."""
    if time.time() > expires:
        return False
    expected = _sign_download_token(object_path, expires)
    return hmac.compare_digest(token, expected)


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
