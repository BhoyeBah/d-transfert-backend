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
    exchange_rate: Decimal | None = Field(
        default=None,
        gt=0,
        description="Taux appliqué, requis uniquement lorsque l'opération implique deux devises différentes.",
    )
    lines: list[NationalOperationLineRequest] = Field(min_length=2)

    @model_validator(mode="after")
    def _validate_balance_per_currency(self) -> "NationalOperationCreateRequest":
        totals: dict[str, Decimal] = {}
        for line in self.lines:
            totals.setdefault(line.currency, Decimal("0"))
            totals[line.currency] += line.amount_in - line.amount_out

        if len(totals) == 1:
            if self.exchange_rate is not None:
                raise ValueError("Le taux de change ne s'applique qu'aux opérations impliquant deux devises.")
            total = next(iter(totals.values()))
            if total != 0:
                raise ValueError(f"Opération non équilibrée (total entrées != total sorties) : écart {total}")
        elif len(totals) == 2:
            if self.exchange_rate is None:
                raise ValueError("Un taux de change est requis pour une opération impliquant deux devises.")
            (currency_a, total_a), (currency_b, total_b) = totals.items()
            if total_a < 0 and total_b > 0:
                source_total, dest_total = total_a, total_b
            elif total_b < 0 and total_a > 0:
                source_total, dest_total = total_b, total_a
            else:
                raise ValueError(
                    "Une opération multi-devises doit avoir une devise source (sortie nette) "
                    "et une devise destination (entrée nette)."
                )
            expected_dest = (-source_total) * self.exchange_rate
            if abs(expected_dest - dest_total) > Decimal("0.01"):
                raise ValueError(
                    f"Montant converti incohérent avec le taux fourni : attendu {expected_dest}, obtenu {dest_total}."
                )
        else:
            raise ValueError("Une opération ne peut impliquer que 1 ou 2 devises différentes à la fois.")
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
    exchange_rate: Decimal | None
    proof_id: uuid.UUID | None
    created_by_id: uuid.UUID
    validated_at: datetime | None
    cancelled_at: datetime | None
    reversal_of_id: uuid.UUID | None
    created_at: datetime
    lines: list[NationalOperationLineResponse]
