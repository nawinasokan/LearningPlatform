from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Interview Academy"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://interview_user:interview_pass@postgres:5432/interview_academy"
    SYNC_DATABASE_URL: str = "postgresql://interview_user:interview_pass@postgres:5432/interview_academy"
    SANDBOX_DATABASE_URL: str = "postgresql://interview_user:interview_pass@postgres:5432/interview_sandbox"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Auth
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:80"

    # File uploads
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        if isinstance(value, str) and value.lower() in {"release", "production", "prod", "0", "false", "no"}:
            return False
        if isinstance(value, str) and value.lower() in {"debug", "development", "dev", "1", "true", "yes"}:
            return True
        return value

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
