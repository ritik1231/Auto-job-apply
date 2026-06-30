from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str

    # Database
    DATABASE_URL: str | None = None

    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # JWT
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_PRIVATE_KEY_PATH: str = "./secrets/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "./secrets/public.pem"
    JWT_PRIVATE_KEY: str | None = None
    JWT_PUBLIC_KEY: str | None = None

    # Gmail token encryption
    GMAIL_TOKEN_ENCRYPTION_KEY: str | None = None

    # AI — provider keys (at least one required)
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GROQ_API_KEY: str | None = None
    GROQ_API_KEY_2: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    AI_MAX_RESUME_TOKENS: int = 4000
    AI_MAX_JOB_POST_TOKENS: int = 2000

    # Per-user daily limits (enforced before AI calls; tokens used for internal billing tracking)
    USER_DAILY_TOKEN_LIMIT: int = 50000  # total input+output tokens per user per day
    USER_DAILY_REQUEST_LIMIT: int = 30  # max analysis flows per user per day

    # File Storage
    RESUME_STORAGE_PATH: str = "./storage/resumes"
    RESUME_MAX_SIZE_MB: int = 5
    RESUME_STORAGE_BACKEND: str = "local"

    # Supabase S3-compatible storage
    SUPABASE_S3_ENDPOINT: str | None = None
    SUPABASE_S3_REGION: str | None = None
    SUPABASE_S3_ACCESS_KEY: str | None = None
    SUPABASE_S3_SECRET_KEY: str | None = None
    SUPABASE_BUCKET_NAME: str = "smartapply-resumes"

    # CORS
    CORS_ALLOWED_ORIGINS_RAW: str = ""

    # Rate Limiting (API-level, separate from user daily limits)
    RATE_LIMIT_JOB_EXTRACT: str = "20/minute"
    RATE_LIMIT_APPLICATION: str = "10/minute"
    RATE_LIMIT_RESUME_UPLOAD: str = "5/hour"

    @property
    def cors_allowed_origins(self) -> list[str]:
        v = self.CORS_ALLOWED_ORIGINS_RAW.strip()
        if not v:
            return []
        return v.split()

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
