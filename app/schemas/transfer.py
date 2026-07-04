import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.transfer import SendMode, TransferStatus
from app.utils.currency import is_supported_currency


class TransferCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collaboration_id: uuid.UUID
    entry_id: uuid.UUID | None = None
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=8)
    beneficiary_name: str | None = Field(default=None, max_length=255)
    beneficiary_phone: str = Field(min_length=1, max_length=32)
    send_mode: SendMode
    note: str | None = Field(default=None, max_length=255)
    client_name: str | None = Field(
        default=None, max_length=255, description="Utilisé si le montant dépasse le disponible de l'entrée."
    )
    client_phone: str | None = Field(default=None, max_length=32)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        if not is_supported_currency(value):
            raise ValueError(f"Devise non supportée : {value}")
        return value.upper()


class TransferApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proof_id: uuid.UUID | None = None


class TransferRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=255)


class TransferResponse(BaseModel):
    id: uuid.UUID
    reference: str
    company_id: uuid.UUID
    collaboration_id: uuid.UUID
    entry_id: uuid.UUID | None
    client_id: uuid.UUID | None
    client_debt_amount: Decimal | None
    amount: Decimal
    currency: str
    beneficiary_name: str | None
    beneficiary_phone: str
    send_mode: SendMode
    note: str | None
    private_rate_used: Decimal | None
    collaborative_rate_used: Decimal
    converted_amount: Decimal
    status: TransferStatus
    proof_id: uuid.UUID | None
    created_by_id: uuid.UUID
    approved_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None
    created_at: datetime


class TransferStatusHistoryResponse(BaseModel):
    id: uuid.UUID
    old_status: TransferStatus | None
    new_status: TransferStatus
    company_id: uuid.UUID
    reason: str | None
    created_at: datetime


class CollaboratorBalanceResponse(BaseModel):
    collaboration_id: uuid.UUID
    currency: str
    balance: Decimal
