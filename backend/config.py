from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SUPERADMIN_USERNAME: str
    SUPERADMIN_PASSWORD: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Convert environment variable names to uppercase
        case_sensitive = False
        extra = "ignore"


settings = Settings()
