import pytest

from app.core.config import (
    DEFAULT_JWT_SECRET_KEY,
    DEFAULT_SUPER_ADMIN_PASSWORD,
    Settings,
    _validate_production_settings,
)


def _valid_production_settings(**overrides) -> Settings:
    defaults = dict(
        environment="production",
        jwt_secret_key="a-real-generated-secret",
        super_admin_initial_password="a-real-generated-password",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_production_with_default_secret_is_rejected():
    settings = _valid_production_settings(jwt_secret_key=DEFAULT_JWT_SECRET_KEY)
    with pytest.raises(RuntimeError):
        _validate_production_settings(settings)


def test_production_with_custom_secret_is_accepted():
    settings = _valid_production_settings()
    _validate_production_settings(settings)


def test_development_with_default_secret_is_accepted():
    settings = Settings(environment="development", jwt_secret_key=DEFAULT_JWT_SECRET_KEY)
    _validate_production_settings(settings)


def test_production_with_default_super_admin_password_is_rejected():
    settings = _valid_production_settings(super_admin_initial_password=DEFAULT_SUPER_ADMIN_PASSWORD)
    with pytest.raises(RuntimeError):
        _validate_production_settings(settings)


def test_development_with_default_super_admin_password_is_accepted():
    settings = Settings(environment="development", super_admin_initial_password=DEFAULT_SUPER_ADMIN_PASSWORD)
    _validate_production_settings(settings)
