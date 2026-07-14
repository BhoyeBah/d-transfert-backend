import pytest

from app.core.config import DEFAULT_JWT_SECRET_KEY, Settings, _validate_production_settings


def test_production_with_default_secret_is_rejected():
    settings = Settings(environment="production", jwt_secret_key=DEFAULT_JWT_SECRET_KEY)
    with pytest.raises(RuntimeError):
        _validate_production_settings(settings)


def test_production_with_custom_secret_is_accepted():
    settings = Settings(environment="production", jwt_secret_key="a-real-generated-secret")
    _validate_production_settings(settings)


def test_development_with_default_secret_is_accepted():
    settings = Settings(environment="development", jwt_secret_key=DEFAULT_JWT_SECRET_KEY)
    _validate_production_settings(settings)
