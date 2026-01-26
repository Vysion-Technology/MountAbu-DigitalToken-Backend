"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Mount Abu E-Token API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # API
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: List[str] = ["*"]

    # Database
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_NAME: str = "mountabu_etoken"

    @property
    def DATABASE_URL(self) -> str:
        """Construct async database URL."""
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Construct sync database URL for Alembic migrations."""
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # JWT Authentication
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OTP Settings
    OTP_EXPIRE_SECONDS: int = 300  # 5 minutes
    OTP_LENGTH: int = 6

    # SMS Provider (MSG91)
    SMS_PROVIDER: str = "msg91"  # msg91, twilio
    MSG91_AUTH_KEY: str = ""
    MSG91_SENDER_ID: str = "MNTABU"
    MSG91_TEMPLATE_ID: str = ""

    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_DOCUMENT_TYPES: List[str] = ["pdf", "jpg", "jpeg", "png"]
    ALLOWED_IMAGE_TYPES: List[str] = ["jpg", "jpeg", "png"]

    # S3/MinIO Storage (optional)
    S3_ENDPOINT: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "etoken-files"
    S3_REGION: str = "us-east-1"

    @property
    def USE_S3_STORAGE(self) -> bool:
        """Check if S3 storage is configured."""
        return bool(self.S3_ENDPOINT and self.S3_ACCESS_KEY and self.S3_SECRET_KEY)

    # Application Rules
    BLACKLIST_REJECTION_THRESHOLD: int = 3  # Auto-blacklist after 3 consecutive rejections
    TOKEN_DEFAULT_VALIDITY_DAYS: int = 60
    APPLICATION_SLA_DAYS: int = 7

    # Mount Abu Coordinates (for geo-validation)
    MOUNTABU_LAT_MIN: float = 24.50
    MOUNTABU_LAT_MAX: float = 24.65
    MOUNTABU_LON_MIN: float = 72.65
    MOUNTABU_LON_MAX: float = 72.80


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
