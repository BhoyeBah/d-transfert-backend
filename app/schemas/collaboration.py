import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.collaboration import CollaborationStatus, RateProposalStatus
from app.utils.currency import is_supported_currency


class CollaborationRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_matricule: str = Field(min_length=1)
    currency: str = Field(min_length=3, max_length=8)
    initial_rate: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        if not is_supported_currency(value):
            raise ValueError(f"Devise non supportée : {value}")
        return value.upper()


class CollaborationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=255)


class RateProposalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_rate: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)


class RateProposalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=255)


class CollaborationResponse(BaseModel):
    id: uuid.UUID
    initiator_company_id: uuid.UUID
    target_company_id: uuid.UUID
    currency: str
    status: CollaborationStatus
    note: str | None
    current_rate: Decimal | None
    created_at: datetime


class CollaborationRateHistoryResponse(BaseModel):
    id: uuid.UUID
    old_rate: Decimal | None
    new_rate: Decimal
    status: RateProposalStatus
    proposed_by_company_id: uuid.UUID
    decided_by_company_id: uuid.UUID | None
    note: str | None
    created_at: datetime
    decided_at: datetime | None
