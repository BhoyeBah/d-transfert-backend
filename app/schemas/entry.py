import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.entry import EntryStatus
from app.models.entry_allocation import EntryAllocationTargetType
from app.utils.currency import is_supported_currency


class EntryLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wallet_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=8)
    note: str | None = Field(default=None, max_length=255)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        if not is_supported_currency(value):
            raise ValueError(f"Devise non supportée : {value}")
        return value.upper()


class EntryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_name: str | None = Field(default=None, max_length=255)
    client_phone: str | None = Field(default=None, max_length=32)
    note: str | None = Field(default=None, max_length=255)
    lines: list[EntryLineRequest] = Field(min_length=1)


class EntryMergeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_ids: list[uuid.UUID] = Field(min_length=2)
    note: str | None = Field(default=None, max_length=255)


class EntryLineResponse(BaseModel):
    wallet_id: uuid.UUID
    amount: Decimal
    currency: str
    note: str | None


class EntryAllocationResponse(BaseModel):
    target_type: EntryAllocationTargetType
    target_id: uuid.UUID
    currency: str
    amount_allocated: Decimal
    created_at: datetime


class EntryResponse(BaseModel):
    id: uuid.UUID
    reference: str
    status: EntryStatus
    client_name: str | None
    client_phone: str | None
    note: str | None
    merged_into_id: uuid.UUID | None
    created_by_id: uuid.UUID
    created_at: datetime
    lines: list[EntryLineResponse]
    allocations: list[EntryAllocationResponse]
    available_by_currency: dict[str, Decimal]
