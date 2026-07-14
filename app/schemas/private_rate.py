import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.transfer import SendMode
from app.utils.currency import is_supported_currency


class PrivateRateCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collaboration_id: uuid.UUID | None = None
    country: str | None = Field(default=None, max_length=64)
    operation_type: SendMode | None = Field(
        default=None, description="Type d'opération (mode d'envoi) auquel ce taux s'applique, si nécessaire."
    )
    currency: str = Field(min_length=3, max_length=8, description="Devise SOURCE de l'envoi.")
    target_currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=8,
        description=(
            "Devise CIBLE de la paire (ex. XOF -> GNF). Si absente et sans collaboration liée : "
            "le taux s'applique à toute devise de destination (comportement historique)."
        ),
    )
    rate: Decimal = Field(gt=0)

    @field_validator("currency", "target_currency")
    @classmethod
    def _validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not is_supported_currency(value):
            raise ValueError(f"Devise non supportée : {value}")
        return value.upper()


class PrivateRateStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool


class PrivateRateResponse(BaseModel):
    id: uuid.UUID
    collaboration_id: uuid.UUID | None
    country: str | None
    operation_type: str | None
    currency: str
    target_currency: str | None
    rate: Decimal
    is_active: bool
    created_at: datetime
    deactivated_at: datetime | None
