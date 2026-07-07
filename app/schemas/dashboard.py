import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class DashboardAlert(BaseModel):
    severity: Literal["info", "warning", "critical"]
    message: str


class CollaboratorBalanceSummary(BaseModel):
    collaboration_id: uuid.UUID
    collaborator_company_id: uuid.UUID
    collaborator_company_name: str
    collaborator_company_matricule: str
    currency: str
    balance: Decimal


class DashboardResponse(BaseModel):
    wallets_balance_by_currency: dict[str, Decimal]
    collaborator_balances: list[CollaboratorBalanceSummary]
    active_collaborations_count: int
    entries_today_count: int
    national_operations_today_count: int
    transfers_today_count: int
    transfers_pending_count: int
    transfers_rejected_count: int
    payments_today_count: int
    payments_pending_count: int
    payments_rejected_count: int
    clients_total_balance: Decimal
    suppliers_total_balance: Decimal
    unread_notifications_count: int
    alerts: list[DashboardAlert]


class EmployeeDashboardResponse(BaseModel):
    entries_created_today_count: int
    transfers_initiated_today_count: int
    payments_initiated_today_count: int
    own_pending_transfers_count: int
    own_pending_payments_count: int
    wallets_count: int


class DailyReportResponse(BaseModel):
    date: str
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
