import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.currency import is_supported_currency


class PrivateRateCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collaboration_id: uuid.UUID | None = None
    country: str | None = Field(default=None, max_length=64)
    currency: str = Field(min_length=3, max_length=8)
    rate: Decimal = Field(gt=0)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        if not is_supported_currency(value):
            raise ValueError(f"Devise non supportée : {value}")
        return value.upper()


class PrivateRateResponse(BaseModel):
    id: uuid.UUID
    collaboration_id: uuid.UUID | None
    country: str | None
    currency: str
    rate: Decimal
    is_active: bool
    created_at: datetime
    deactivated_at: datetime | None
