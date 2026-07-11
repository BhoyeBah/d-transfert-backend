import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.wallet import WalletStatus, WalletType
from app.models.wallet_movement import MovementDirection
from app.utils.currency import is_supported_currency


class WalletCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=128)
    code: str = Field(min_length=2, max_length=32)
    type: WalletType
    phone: str | None = Field(default=None, max_length=32)
    currency: str = Field(min_length=3, max_length=8)
    initial_balance: Decimal = Field(default=Decimal("0"), ge=0)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        if not is_supported_currency(value):
            raise ValueError(f"Devise non supportée : {value}")
        return value.upper()


class WalletUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=128)
    phone: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=255)


class WalletStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: WalletStatus


class WalletResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    type: WalletType
    phone: str | None
    currency: str
    balance: Decimal
    status: WalletStatus
    description: str | None
    created_at: datetime


class WalletOptionResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    currency: str
    status: WalletStatus


class WalletMovementResponse(BaseModel):
    id: uuid.UUID
    direction: MovementDirection
    amount: Decimal
    currency: str
    balance_before: Decimal
    balance_after: Decimal
    source_type: str
    source_id: uuid.UUID
    created_by_id: uuid.UUID
    note: str | None
    created_at: datetime
