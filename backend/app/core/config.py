from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict


class _TolerantEnvSource(EnvSettingsSource):
    """Fall back to space-splitting when a list field contains a non-JSON string."""

    def decode_complex_value(
        self, field_name: str, field_info: "FieldInfo", value: object
    ) -> object:  # type: ignore[override]
        try:
            return super().decode_complex_value(field_name, field_info, value)
        except Exception:
            if isinstance(value, str) and value.strip():
                return value.split()
            return []


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, secrets_settings, **kwargs
    ):  # type: ignore[override]
        return (init_settings, _TolerantEnvSource(settings_cls), dotenv_settings, secrets_settings)

    # Application
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str  # required — no default; fails fast if absent

    # Database (required from Phase 4 onward)
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
    # Production alternative: base64-encoded PEM strings set as env vars.
    # Generate: base64 secrets/private.pem | tr -d '\n'
    JWT_PRIVATE_KEY: str | None = None
    JWT_PUBLIC_KEY: str | None = None

    # Gmail token encryption
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    GMAIL_TOKEN_ENCRYPTION_KEY: str | None = None

    # AI
    AI_PROVIDER: str = "gemini"  # gemini | groq
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    AI_MAX_RESUME_TOKENS: int = 4000
    AI_MAX_JOB_POST_TOKENS: int = 2000

    # File Storage
    RESUME_STORAGE_PATH: str = "./storage/resumes"
    RESUME_MAX_SIZE_MB: int = 5
    RESUME_STORAGE_BACKEND: str = "local"  # local | supabase

    # Supabase S3-compatible storage
    SUPABASE_S3_ENDPOINT: str | None = None
    SUPABASE_S3_REGION: str | None = None
    SUPABASE_S3_ACCESS_KEY: str | None = None
    SUPABASE_S3_SECRET_KEY: str | None = None
    SUPABASE_BUCKET_NAME: str = "smartapply-resumes"

    # CORS — space-separated string or JSON array: chrome-extension://id http://localhost:3000
    CORS_ALLOWED_ORIGINS: list[str] = []

    # Rate Limiting
    RATE_LIMIT_JOB_EXTRACT: str = "20/minute"
    RATE_LIMIT_APPLICATION: str = "10/minute"
    RATE_LIMIT_RESUME_UPLOAD: str = "5/hour"

    # Dynamic daily quota
    # Total AI budget = requests the shared LLM key can serve per day.
    # Cap per user = clamp(DAILY_AI_BUDGET // active_users, MIN, MAX).
    DAILY_AI_BUDGET: int = 4800  # Groq free tier: 14400 req/day ÷ 3 calls/app
    QUOTA_MAX_PER_USER: int = 20  # never give more than 20/day even with 1 user
    QUOTA_MIN_PER_USER: int = 3  # always allow at least 3/day

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str) and v:
            return v.split()
        return []

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
