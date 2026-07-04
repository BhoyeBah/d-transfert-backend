import csv
import io
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaboration import Collaboration, CollaborationStatus
from app.models.national_operation import NationalOperationType
from app.models.payment import PaymentStatus
from app.models.transfer import TransferStatus
from app.models.wallet import WalletStatus
from app.repositories import (
    client_repository,
    collaboration_repository,
    collaborator_balance_repository,
    entry_repository,
    national_operation_repository,
    notification_repository,
    payment_repository,
    supplier_repository,
    transfer_repository,
    wallet_repository,
)
from app.schemas.dashboard import CollaboratorBalanceSummary, DailyReportResponse, DashboardResponse


def _other_party(collaboration: Collaboration, company_id: uuid.UUID) -> uuid.UUID:
    if collaboration.initiator_company_id == company_id:
        return collaboration.target_company_id
    return collaboration.initiator_company_id


def _is_today(created_at: datetime) -> bool:
    return created_at.astimezone(timezone.utc).date() == datetime.now(timezone.utc).date()


def _is_on_date(created_at: datetime, target_date) -> bool:
    return created_at.astimezone(timezone.utc).date() == target_date


async def build_dashboard(session: AsyncSession, company_id: uuid.UUID) -> DashboardResponse:
    wallets = await wallet_repository.list_by_company(session, company_id)
    wallets_balance_by_currency: dict[str, Decimal] = defaultdict(Decimal)
    for wallet in wallets:
        if wallet.status == WalletStatus.ACTIVE:
            wallets_balance_by_currency[wallet.currency] += wallet.balance

    collaborations = await collaboration_repository.list_for_company(session, company_id)
    collaborator_balances = []
    active_collaborations_count = 0
    for collaboration in collaborations:
        if collaboration.status != CollaborationStatus.ACCEPTED:
            continue
        active_collaborations_count += 1
        balance = await collaborator_balance_repository.get_balance_for_company(
            session, collaboration.id, company_id
        )
        collaborator_balances.append(
            CollaboratorBalanceSummary(
                collaboration_id=collaboration.id,
                collaborator_company_id=_other_party(collaboration, company_id),
                currency=collaboration.currency,
                balance=balance,
            )
        )

    entries = await entry_repository.list_by_company(session, company_id)
    entries_today_count = sum(1 for entry in entries if _is_today(entry.created_at))

    national_operations = await national_operation_repository.list_by_company(session, company_id)
    national_operations_today_count = sum(
        1 for operation in national_operations if _is_today(operation.created_at)
    )

    transfers = await transfer_repository.list_for_company(session, company_id)
    transfers_today_count = sum(1 for transfer in transfers if _is_today(transfer.created_at))
    transfers_pending_count = sum(1 for transfer in transfers if transfer.status == TransferStatus.PENDING)
    transfers_rejected_count = sum(
        1 for transfer in transfers if transfer.status == TransferStatus.REJECTED
    )

    payments = await payment_repository.list_for_company(session, company_id)
    payments_today_count = sum(1 for payment in payments if _is_today(payment.created_at))
    payments_pending_count = sum(1 for payment in payments if payment.status == PaymentStatus.PENDING)
    payments_rejected_count = sum(1 for payment in payments if payment.status == PaymentStatus.REJECTED)

    clients = await client_repository.list_by_company(session, company_id)
    clients_total_balance = sum((c.balance for c in clients), Decimal("0.00"))

    suppliers = await supplier_repository.list_by_company(session, company_id)
    suppliers_total_balance = sum((s.balance for s in suppliers), Decimal("0.00"))

    notifications = await notification_repository.list_by_company(session, company_id)
    unread_notifications_count = sum(1 for n in notifications if not n.is_read)

    return DashboardResponse(
        wallets_balance_by_currency=dict(wallets_balance_by_currency),
        collaborator_balances=collaborator_balances,
        active_collaborations_count=active_collaborations_count,
        entries_today_count=entries_today_count,
        national_operations_today_count=national_operations_today_count,
        transfers_today_count=transfers_today_count,
        transfers_pending_count=transfers_pending_count,
        transfers_rejected_count=transfers_rejected_count,
        payments_today_count=payments_today_count,
        payments_pending_count=payments_pending_count,
        payments_rejected_count=payments_rejected_count,
        clients_total_balance=clients_total_balance,
        suppliers_total_balance=suppliers_total_balance,
        unread_notifications_count=unread_notifications_count,
    )


async def build_daily_report(session: AsyncSession, company_id: uuid.UUID, report_date) -> DailyReportResponse:
    national_operations = await national_operation_repository.list_by_company(session, company_id)
    day_operations = [op for op in national_operations if _is_on_date(op.created_at, report_date)]

    entries = await entry_repository.list_by_company(session, company_id)
    day_entries = [entry for entry in entries if _is_on_date(entry.created_at, report_date)]
    entries_total_by_currency: dict[str, Decimal] = defaultdict(Decimal)
    for entry in day_entries:
        lines = await entry_repository.get_lines(session, entry.id)
        for line in lines:
            entries_total_by_currency[line.currency] += line.amount

    transfers = await transfer_repository.list_for_company(session, company_id)
    day_transfers = [t for t in transfers if _is_on_date(t.created_at, report_date)]

    payments = await payment_repository.list_for_company(session, company_id)
    day_payments = [p for p in payments if _is_on_date(p.created_at, report_date)]

    return DailyReportResponse(
        date=report_date.isoformat(),
        deposits_count=sum(1 for op in day_operations if op.type == NationalOperationType.DEPOSIT),
        withdrawals_count=sum(1 for op in day_operations if op.type == NationalOperationType.WITHDRAWAL),
        exchanges_count=sum(1 for op in day_operations if op.type == NationalOperationType.EXCHANGE),
        rebalances_count=sum(1 for op in day_operations if op.type == NationalOperationType.REBALANCE),
        entries_count=len(day_entries),
        entries_total_by_currency=dict(entries_total_by_currency),
        transfers_created_count=len(day_transfers),
        transfers_approved_count=sum(1 for t in day_transfers if t.status == TransferStatus.APPROVED),
        transfers_rejected_count=sum(1 for t in day_transfers if t.status == TransferStatus.REJECTED),
        payments_created_count=len(day_payments),
        payments_approved_count=sum(1 for p in day_payments if p.status == PaymentStatus.APPROVED),
        payments_rejected_count=sum(1 for p in day_payments if p.status == PaymentStatus.REJECTED),
    )


def daily_report_to_csv(report: DailyReportResponse) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["metric", "value"])
    writer.writerow(["date", report.date])
    writer.writerow(["deposits_count", report.deposits_count])
    writer.writerow(["withdrawals_count", report.withdrawals_count])
    writer.writerow(["exchanges_count", report.exchanges_count])
    writer.writerow(["rebalances_count", report.rebalances_count])
    writer.writerow(["entries_count", report.entries_count])
    for currency, amount in report.entries_total_by_currency.items():
        writer.writerow([f"entries_total_{currency}", amount])
    writer.writerow(["transfers_created_count", report.transfers_created_count])
    writer.writerow(["transfers_approved_count", report.transfers_approved_count])
    writer.writerow(["transfers_rejected_count", report.transfers_rejected_count])
    writer.writerow(["payments_created_count", report.payments_created_count])
    writer.writerow(["payments_approved_count", report.payments_approved_count])
    writer.writerow(["payments_rejected_count", report.payments_rejected_count])
    return buffer.getvalue()
