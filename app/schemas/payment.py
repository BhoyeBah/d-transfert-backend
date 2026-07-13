import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.payment import PaymentStatus
from app.utils.currency import is_supported_currency

ReliquatAction = Literal["unallocated", "fee", "client_credit"]


class PaymentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collaboration_id: uuid.UUID
    entry_id: uuid.UUID | None = None
    wallet_id: uuid.UUID | None = None
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=8)
    client_name: str | None = Field(default=None, max_length=255)
    client_phone: str | None = Field(default=None, max_length=32)
    note: str | None = Field(default=None, max_length=255)
    reliquat_action: ReliquatAction = Field(
        default="unallocated",
        description=(
            "Traitement du reliquat si le montant déclaré est inférieur au disponible de l'entrée : "
            "'unallocated' (reste disponible), 'fee' (conservé comme frais), "
            "'client_credit' (crédité au solde du client)."
        ),
    )

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        if not is_supported_currency(value):
            raise ValueError(f"Devise non supportée : {value}")
        return value.upper()

    @model_validator(mode="after")
    def _entry_and_wallet_mutually_exclusive(self) -> "PaymentCreateRequest":
        if self.entry_id is not None and self.wallet_id is not None:
            raise ValueError("Un paiement ne peut pas référencer à la fois une entrée et un wallet.")
        return self


class PaymentApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proof_id: uuid.UUID | None = None


class PaymentRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=255)


class PaymentResponse(BaseModel):
    id: uuid.UUID
    reference: str
    company_id: uuid.UUID
    collaboration_id: uuid.UUID
    entry_id: uuid.UUID | None
    wallet_id: uuid.UUID | None
    client_id: uuid.UUID | None
    client_debt_amount: Decimal | None
    amount: Decimal
    currency: str
    client_name: str | None
    client_phone: str | None
    note: str | None
    collaborative_rate_used: Decimal
    converted_amount: Decimal
    settles_debt: bool
    status: PaymentStatus
    proof_id: uuid.UUID | None
    created_by_id: uuid.UUID
    approved_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None
    created_at: datetime


class PaymentStatusHistoryResponse(BaseModel):
    id: uuid.UUID
    old_status: PaymentStatus | None
    new_status: PaymentStatus
    company_id: uuid.UUID
    reason: str | None
    created_at: datetime
