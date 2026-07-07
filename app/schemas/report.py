import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class MonthlyReportResponse(BaseModel):
    month: str
    deposits_count: int
    withdrawals_count: int
    exchanges_count: int
    rebalances_count: int
    entries_count: int
    entries_total_by_currency: dict[str, Decimal]
    transfers_created_count: int
    transfers_approved_count: int
    transfers_rejected_count: int
    payments_created_count: int
    payments_approved_count: int
    payments_rejected_count: int


class TransactionReportRow(BaseModel):
    kind: str
    reference: str
    type_or_mode: str
    amount: Decimal | None
    currency: str | None
    status: str
    created_at: datetime


class WalletMovementReportRow(BaseModel):
    id: uuid.UUID
    direction: str
    amount: Decimal
    currency: str
    balance_before: Decimal
    balance_after: Decimal
    source_type: str
    source_id: uuid.UUID
    note: str | None
    created_at: datetime


class EmployeeActivityRow(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    note: str | None
    created_at: datetime


class SupplierMovementReportRow(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    reference: str
    type: str
    amount: Decimal
    balance_after: Decimal
    created_at: datetime


class ClientMovementReportRow(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    delta: Decimal
    balance_after: Decimal
    source_type: str
    created_at: datetime


class FeeReportRow(BaseModel):
    source_type: str
    source_id: uuid.UUID | None
    amount: Decimal
    currency: str
    created_at: datetime


class RejectedOperationReportRow(BaseModel):
    kind: str
    reference: str
    reason: str | None
    created_at: datetime
