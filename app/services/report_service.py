import csv
import io
import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.collaboration import CollaborationStatus
from app.models.national_operation import NationalOperationStatus, NationalOperationType
from app.models.payment import PaymentStatus
from app.models.transfer import TransferStatus
from app.repositories import (
    audit_log_repository,
    client_repository,
    collaboration_repository,
    collaborator_balance_repository,
    company_repository,
    entry_repository,
    national_operation_repository,
    payment_repository,
    supplier_repository,
    transfer_repository,
    user_repository,
    wallet_movement_repository,
    wallet_repository,
)
from app.schemas.dashboard import CollaboratorBalanceSummary
from app.schemas.report import (
    ClientMovementReportRow,
    EmployeeActivityRow,
    FeeReportRow,
    MonthlyReportResponse,
    RejectedOperationReportRow,
    SupplierMovementReportRow,
    TransactionReportRow,
    WalletMovementReportRow,
)

_FEE_NOTE_PATTERN = re.compile(r"action=fee amount=([\d.]+) (\S+)")


def _in_period(created_at: datetime, date_from: date | None, date_to: date | None) -> bool:
    day = created_at.astimezone(timezone.utc).date()
    if date_from is not None and day < date_from:
        return False
    if date_to is not None and day > date_to:
        return False
    return True


def rows_to_csv(rows: list[BaseModel], model_cls: type[BaseModel]) -> str:
    buffer = io.StringIO()
    fieldnames = list(model_cls.model_fields.keys())
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: ("" if value is None else str(value)) for key, value in row.model_dump().items()})
    return buffer.getvalue()


async def _aggregate_period(session: AsyncSession, company_id: uuid.UUID, date_from: date, date_to: date) -> dict:
    national_operations = await national_operation_repository.list_by_company(session, company_id)
    period_operations = [op for op in national_operations if _in_period(op.created_at, date_from, date_to)]

    entries = await entry_repository.list_by_company(session, company_id)
    period_entries = [entry for entry in entries if _in_period(entry.created_at, date_from, date_to)]
    entries_total_by_currency: dict[str, Decimal] = defaultdict(Decimal)
    for entry in period_entries:
        lines = await entry_repository.get_lines(session, entry.id)
        for line in lines:
            entries_total_by_currency[line.currency] += line.amount

    transfers = await transfer_repository.list_for_company(session, company_id)
    period_transfers = [t for t in transfers if _in_period(t.created_at, date_from, date_to)]

    payments = await payment_repository.list_for_company(session, company_id)
    period_payments = [p for p in payments if _in_period(p.created_at, date_from, date_to)]

    return {
        "deposits_count": sum(1 for op in period_operations if op.type == NationalOperationType.DEPOSIT),
        "withdrawals_count": sum(1 for op in period_operations if op.type == NationalOperationType.WITHDRAWAL),
        "exchanges_count": sum(1 for op in period_operations if op.type == NationalOperationType.EXCHANGE),
        "rebalances_count": sum(1 for op in period_operations if op.type == NationalOperationType.REBALANCE),
        "entries_count": len(period_entries),
        "entries_total_by_currency": dict(entries_total_by_currency),
        "transfers_created_count": len(period_transfers),
        "transfers_approved_count": sum(1 for t in period_transfers if t.status == TransferStatus.APPROVED),
        "transfers_rejected_count": sum(1 for t in period_transfers if t.status == TransferStatus.REJECTED),
        "payments_created_count": len(period_payments),
        "payments_approved_count": sum(1 for p in period_payments if p.status == PaymentStatus.APPROVED),
        "payments_rejected_count": sum(1 for p in period_payments if p.status == PaymentStatus.REJECTED),
    }


async def build_monthly_report(
    session: AsyncSession, company_id: uuid.UUID, year: int, month: int
) -> MonthlyReportResponse:
    start = date(year, month, 1)
    end = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    data = await _aggregate_period(session, company_id, start, end)
    return MonthlyReportResponse(month=f"{year:04d}-{month:02d}", **data)


def monthly_report_to_csv(report: MonthlyReportResponse) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["metric", "value"])
    writer.writerow(["month", report.month])
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


async def build_transactions_report(
    session: AsyncSession, company_id: uuid.UUID, date_from: date | None, date_to: date | None
) -> list[TransactionReportRow]:
    rows: list[TransactionReportRow] = []

    transfers = await transfer_repository.list_for_company(session, company_id)
    for transfer in transfers:
        if _in_period(transfer.created_at, date_from, date_to):
            rows.append(
                TransactionReportRow(
                    kind="transfer",
                    reference=transfer.reference,
                    type_or_mode=transfer.send_mode.value,
                    amount=transfer.amount,
                    currency=transfer.currency,
                    status=transfer.status.value,
                    created_at=transfer.created_at,
                )
            )

    payments = await payment_repository.list_for_company(session, company_id)
    for payment in payments:
        if _in_period(payment.created_at, date_from, date_to):
            rows.append(
                TransactionReportRow(
                    kind="payment",
                    reference=payment.reference,
                    type_or_mode="payment",
                    amount=payment.amount,
                    currency=payment.currency,
                    status=payment.status.value,
                    created_at=payment.created_at,
                )
            )

    operations = await national_operation_repository.list_by_company(session, company_id)
    for operation in operations:
        if _in_period(operation.created_at, date_from, date_to):
            rows.append(
                TransactionReportRow(
                    kind="national_operation",
                    reference=operation.reference,
                    type_or_mode=operation.type.value,
                    amount=None,
                    currency=None,
                    status=operation.status.value,
                    created_at=operation.created_at,
                )
            )

    rows.sort(key=lambda row: row.created_at)
    return rows


async def build_collaborator_balances_report(
    session: AsyncSession, company_id: uuid.UUID
) -> list[CollaboratorBalanceSummary]:
    collaborations = await collaboration_repository.list_for_company(session, company_id)
    rows: list[CollaboratorBalanceSummary] = []
    for collaboration in collaborations:
        if collaboration.status != CollaborationStatus.ACCEPTED:
            continue
        balance = await collaborator_balance_repository.get_balance_for_company(
            session, collaboration.id, company_id
        )
        collaborator_company_id = (
            collaboration.target_company_id
            if collaboration.initiator_company_id == company_id
            else collaboration.initiator_company_id
        )
        collaborator_company = await company_repository.get_by_id(session, collaborator_company_id)
        rows.append(
            CollaboratorBalanceSummary(
                collaboration_id=collaboration.id,
                collaborator_company_id=collaborator_company_id,
                collaborator_company_name=collaborator_company.name if collaborator_company else "—",
                collaborator_company_matricule=(
                    collaborator_company.registration_code if collaborator_company else "—"
                ),
                currency=collaboration.currency,
                balance=balance,
            )
        )
    return rows


async def build_wallet_history_report(
    session: AsyncSession,
    company_id: uuid.UUID,
    wallet_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
) -> list[WalletMovementReportRow]:
    wallet = await wallet_repository.get_by_company_and_id(session, company_id, wallet_id)
    if wallet is None:
        raise NotFoundError("Wallet introuvable.")
    movements = await wallet_movement_repository.list_by_wallet(session, wallet_id)
    return [
        WalletMovementReportRow(
            id=movement.id,
            direction=movement.direction.value,
            amount=movement.amount,
            currency=movement.currency,
            balance_before=movement.balance_before,
            balance_after=movement.balance_after,
            source_type=movement.source_type,
            source_id=movement.source_id,
            note=movement.note,
            created_at=movement.created_at,
        )
        for movement in movements
        if _in_period(movement.created_at, date_from, date_to)
    ]


async def build_employee_activity_report(
    session: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
) -> list[EmployeeActivityRow]:
    employee = await user_repository.get_by_company_and_id(session, company_id, user_id)
    if employee is None:
        raise NotFoundError("Employé introuvable.")
    logs = await audit_log_repository.list_by_company(session, company_id)
    return [
        EmployeeActivityRow(
            id=log.id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            note=log.note,
            created_at=log.created_at,
        )
        for log in logs
        if log.user_id == user_id and _in_period(log.created_at, date_from, date_to)
    ]


async def build_supplier_report(
    session: AsyncSession, company_id: uuid.UUID, date_from: date | None, date_to: date | None
) -> list[SupplierMovementReportRow]:
    suppliers = await supplier_repository.list_by_company(session, company_id)
    rows: list[SupplierMovementReportRow] = []
    for supplier in suppliers:
        movements = await supplier_repository.list_movements(session, supplier.id)
        for movement in movements:
            if _in_period(movement.created_at, date_from, date_to):
                rows.append(
                    SupplierMovementReportRow(
                        id=movement.id,
                        supplier_id=supplier.id,
                        supplier_name=supplier.name,
                        reference=movement.reference,
                        type=movement.type.value,
                        amount=movement.amount,
                        balance_after=movement.balance_after,
                        created_at=movement.created_at,
                    )
                )
    rows.sort(key=lambda row: row.created_at)
    return rows


async def build_client_report(
    session: AsyncSession, company_id: uuid.UUID, date_from: date | None, date_to: date | None
) -> list[ClientMovementReportRow]:
    clients = await client_repository.list_by_company(session, company_id)
    rows: list[ClientMovementReportRow] = []
    for client in clients:
        movements = await client_repository.list_movements(session, client.id)
        for movement in movements:
            if _in_period(movement.created_at, date_from, date_to):
                rows.append(
                    ClientMovementReportRow(
                        id=movement.id,
                        client_id=client.id,
                        client_name=client.name,
                        delta=movement.delta,
                        balance_after=movement.balance_after,
                        source_type=movement.source_type,
                        created_at=movement.created_at,
                    )
                )
    rows.sort(key=lambda row: row.created_at)
    return rows


async def build_fees_report(
    session: AsyncSession, company_id: uuid.UUID, date_from: date | None, date_to: date | None
) -> list[FeeReportRow]:
    logs = await audit_log_repository.list_by_company(session, company_id)
    rows: list[FeeReportRow] = []
    for log in logs:
        if log.action not in ("transfer.reliquat", "payment.reliquat"):
            continue
        if not _in_period(log.created_at, date_from, date_to):
            continue
        if not log.note:
            continue
        match = _FEE_NOTE_PATTERN.search(log.note)
        if not match:
            continue
        amount, currency = match.groups()
        rows.append(
            FeeReportRow(
                source_type=log.entity_type,
                source_id=log.entity_id,
                amount=Decimal(amount),
                currency=currency,
                created_at=log.created_at,
            )
        )
    return rows


async def build_rejected_operations_report(
    session: AsyncSession, company_id: uuid.UUID, date_from: date | None, date_to: date | None
) -> list[RejectedOperationReportRow]:
    rows: list[RejectedOperationReportRow] = []

    transfers = await transfer_repository.list_for_company(session, company_id)
    for transfer in transfers:
        reference_date = transfer.rejected_at or transfer.created_at
        if transfer.status == TransferStatus.REJECTED and _in_period(reference_date, date_from, date_to):
            rows.append(
                RejectedOperationReportRow(
                    kind="transfer",
                    reference=transfer.reference,
                    reason=transfer.rejection_reason,
                    created_at=reference_date,
                )
            )

    payments = await payment_repository.list_for_company(session, company_id)
    for payment in payments:
        reference_date = payment.rejected_at or payment.created_at
        if payment.status == PaymentStatus.REJECTED and _in_period(reference_date, date_from, date_to):
            rows.append(
                RejectedOperationReportRow(
                    kind="payment",
                    reference=payment.reference,
                    reason=payment.rejection_reason,
                    created_at=reference_date,
                )
            )

    operations = await national_operation_repository.list_by_company(session, company_id)
    for operation in operations:
        reference_date = operation.cancelled_at or operation.created_at
        if operation.status == NationalOperationStatus.CANCELLED and _in_period(reference_date, date_from, date_to):
            rows.append(
                RejectedOperationReportRow(
                    kind="national_operation",
                    reference=operation.reference,
                    reason=None,
                    created_at=reference_date,
                )
            )

    rows.sort(key=lambda row: row.created_at)
    return rows
