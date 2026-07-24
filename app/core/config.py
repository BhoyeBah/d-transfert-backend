from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET_KEY = "dev-only-change-me-32-bytes-minimum-secret-key"
DEFAULT_SUPER_ADMIN_PASSWORD = "dev-only-change-me-super-admin-password"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://dtransfert:dtransfert@localhost:5432/dtransfert"
    jwt_secret_key: str = DEFAULT_JWT_SECRET_KEY
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    upload_dir: str = "uploads"
    backup_dir: str = "backups"
    max_upload_size_mb: int = 10
    # Stockage partagé du rate limiting (voir app/core/rate_limit.py). Laisser vide utilise un
    # compteur en mémoire par processus, ce qui ne tient plus la route dès qu'il y a plusieurs
    # instances backend derrière un load balancer.
    redis_url: str | None = None
    # Mot de passe du compte Super Admin (matricule ADMIN) créé par scripts/seed_super_admin.py
    # UNIQUEMENT s'il n'existe pas encore — jamais réécrit s'il existe déjà, pour ne pas annuler
    # un changement de mot de passe fait depuis l'interface d'administration.
    super_admin_initial_password: str = DEFAULT_SUPER_ADMIN_PASSWORD


def _validate_production_settings(settings: Settings) -> None:
    if settings.environment == "production" and settings.jwt_secret_key == DEFAULT_JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY est encore la valeur par défaut du dépôt alors que ENVIRONMENT=production. "
            "Générez une clé forte et unique (ex. `openssl rand -hex 32`) et définissez-la via une "
            "variable d'environnement avant de démarrer l'application."
        )
    if settings.environment == "production" and settings.super_admin_initial_password == DEFAULT_SUPER_ADMIN_PASSWORD:
        raise RuntimeError(
            "SUPER_ADMIN_INITIAL_PASSWORD est encore la valeur par défaut du dépôt alors que "
            "ENVIRONMENT=production. Définissez un mot de passe fort et unique via une variable "
            "d'environnement avant de démarrer l'application."
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _validate_production_settings(settings)
    return settings
