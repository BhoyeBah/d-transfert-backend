import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.national_operation import NationalOperationStatus, NationalOperationType
from app.utils.currency import is_supported_currency


class NationalOperationLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wallet_id: uuid.UUID
    amount_in: Decimal = Field(default=Decimal("0"), ge=0)
    amount_out: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(min_length=3, max_length=8)
    note: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _validate_single_direction(self) -> "NationalOperationLineRequest":
        if not is_supported_currency(self.currency):
            raise ValueError(f"Devise non supportée : {self.currency}")
        if self.amount_in > 0 and self.amount_out > 0:
            raise ValueError("Une ligne ne peut pas avoir à la fois un montant entrée et un montant sortie.")
        if self.amount_in == 0 and self.amount_out == 0:
            raise ValueError("Une ligne doit avoir un montant entrée ou sortie strictement positif.")
        return self


class NationalOperationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_name: str | None = Field(default=None, max_length=255)
    client_phone: str | None = Field(default=None, max_length=32)
    note: str | None = Field(default=None, max_length=255)
    proof_id: uuid.UUID | None = None
    lines: list[NationalOperationLineRequest] = Field(min_length=2)

    @model_validator(mode="after")
    def _validate_balance_per_currency(self) -> "NationalOperationCreateRequest":
        totals: dict[str, Decimal] = {}
        for line in self.lines:
            totals.setdefault(line.currency, Decimal("0"))
            totals[line.currency] += line.amount_in - line.amount_out
        unbalanced = {currency: total for currency, total in totals.items() if total != 0}
        if unbalanced:
            details = ", ".join(f"{currency}: écart {total}" for currency, total in unbalanced.items())
            raise ValueError(f"Opération non équilibrée (total entrées != total sorties) : {details}")
        return self


class NationalOperationLineResponse(BaseModel):
    wallet_id: uuid.UUID
    amount_in: Decimal
    amount_out: Decimal
    currency: str
    balance_before: Decimal | None
    balance_after: Decimal | None
    note: str | None


class NationalOperationResponse(BaseModel):
    id: uuid.UUID
    reference: str
    type: NationalOperationType
    status: NationalOperationStatus
    client_name: str | None
    client_phone: str | None
    note: str | None
    proof_id: uuid.UUID | None
    created_by_id: uuid.UUID
    validated_at: datetime | None
    cancelled_at: datetime | None
    reversal_of_id: uuid.UUID | None
    created_at: datetime
    lines: list[NationalOperationLineResponse]
