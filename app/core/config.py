from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET_KEY = "dev-only-change-me-32-bytes-minimum-secret-key"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://dtransfert:dtransfert@localhost:5432/dtransfert"
    jwt_secret_key: str = DEFAULT_JWT_SECRET_KEY
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10


def _validate_production_settings(settings: Settings) -> None:
    if settings.environment == "production" and settings.jwt_secret_key == DEFAULT_JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY est encore la valeur par défaut du dépôt alors que ENVIRONMENT=production. "
            "Générez une clé forte et unique (ex. `openssl rand -hex 32`) et définissez-la via une "
            "variable d'environnement avant de démarrer l'application."
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _validate_production_settings(settings)
    return settings
