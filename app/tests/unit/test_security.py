import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify():
    hashed = hash_password("Secret123!")
    assert hashed != "Secret123!"
    assert verify_password("Secret123!", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_and_refresh_tokens_round_trip():
    access = create_access_token(
        "user-1",
        "company-1",
        matricule="DT-000001",
        is_owner=True,
        is_super_admin=False,
    )
    refresh = create_refresh_token(
        "user-1",
        "company-1",
        matricule="DT-000001",
        is_owner=True,
        is_super_admin=False,
    )

    access_payload = decode_token(access, TokenType.ACCESS)
    refresh_payload = decode_token(refresh, TokenType.REFRESH)

    assert access_payload["sub"] == "user-1"
    assert access_payload["company_id"] == "company-1"
    assert access_payload["matricule"] == "DT-000001"
    assert access_payload["is_owner"] is True
    assert access_payload["is_super_admin"] is False
    assert refresh_payload["type"] == "refresh"


def test_token_type_mismatch_is_rejected():
    access = create_access_token("user-1", "company-1")
    with pytest.raises(UnauthorizedError):
        decode_token(access, TokenType.REFRESH)
