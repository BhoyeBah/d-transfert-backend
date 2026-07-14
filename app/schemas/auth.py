import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.currency import is_supported_currency


class MeResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID | None
    matricule: str
    full_name: str
    is_owner: bool
    is_super_admin: bool
    permissions: list[str]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=2, max_length=255)
    company_phone: str = Field(min_length=6, max_length=32)
    address: str = Field(min_length=2, max_length=255)
    default_currency: str = Field(min_length=3, max_length=8)
    owner_full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    password_confirmation: str = Field(min_length=8, max_length=128)

    @field_validator("default_currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        if not is_supported_currency(value):
            raise ValueError(f"Devise non supportée : {value}")
        return value.upper()

    @field_validator("password_confirmation")
    @classmethod
    def _passwords_match(cls, value: str, info) -> str:
        if info.data.get("password") is not None and value != info.data["password"]:
            raise ValueError("Les mots de passe ne correspondent pas.")
        return value


class RegisterResponse(BaseModel):
    company_id: uuid.UUID
    registration_code: str
    owner_user_id: uuid.UUID


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matricule: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matricule: str


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matricule: str
    otp_code: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=8, max_length=128)
    new_password_confirmation: str = Field(min_length=8, max_length=128)

    @field_validator("new_password_confirmation")
    @classmethod
    def _passwords_match(cls, value: str, info) -> str:
        if info.data.get("new_password") is not None and value != info.data["new_password"]:
            raise ValueError("Les mots de passe ne correspondent pas.")
        return value

