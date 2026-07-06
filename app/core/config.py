from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://dtransfert:dtransfert@localhost:5432/dtransfert"
    jwt_secret_key: str = "dev-only-change-me-32-bytes-minimum-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
