import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.supplier_balance_movement import SupplierMovementType
from app.utils.currency import is_supported_currency


class SupplierCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=255)
    currency: str = Field(min_length=3, max_length=8)
    initial_balance: Decimal = Field(default=Decimal("0"))
    note: str | None = Field(default=None, max_length=255)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        if not is_supported_currency(value):
            raise ValueError(f"Devise non supportée : {value}")
        return value.upper()


class SupplierRebalanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: SupplierMovementType
    amount: Decimal = Field(gt=0)
    wallet_id: uuid.UUID
    proof_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=255)


class SupplierResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    phone: str | None
    address: str | None
    currency: str
    note: str | None
    balance: Decimal
    created_at: datetime


class SupplierBalanceMovementResponse(BaseModel):
    id: uuid.UUID
    reference: str
    type: SupplierMovementType
    wallet_id: uuid.UUID
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    proof_id: uuid.UUID | None
    note: str | None
    created_at: datetime
