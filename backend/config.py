from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = True

    SUPERADMIN_USERNAME: str = "admin"
    SUPERADMIN_PASSWORD: str = "admin"

    POSTGRES_USER: str = "etoken_user"
    POSTGRES_PASSWORD: str = "etoken_secure_password_123"
    POSTGRES_DB: str = "mountabu_etoken"
    DATABASE_HOST: str = "postgres"

    MINIO_HOST: str = "minio"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"

    @property
    def database_url(self) -> str:
        # Use asyncpg driver for async sqlalchemy
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.DATABASE_HOST}:5432/{self.POSTGRES_DB}"

    @property
    def sync_database_url(self) -> str:
        # Use psycopg2 (or default) for sync operations if needed, or just remove +asyncpg if using standard driver
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.DATABASE_HOST}:5432/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
