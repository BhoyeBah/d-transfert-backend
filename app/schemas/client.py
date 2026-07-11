import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ClientCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=1, max_length=32)
    note: str | None = Field(default=None, max_length=255)


class ClientCurrencyBalance(BaseModel):
    currency: str
    balance: Decimal


class ClientResponse(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    note: str | None
    balance: Decimal
    balances: list[ClientCurrencyBalance] = Field(default_factory=list)
    created_at: datetime


class ClientBalanceMovementResponse(BaseModel):
    id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    currency: str
    delta: Decimal
    balance_before: Decimal
    balance_after: Decimal
    note: str | None
    created_at: datetime
