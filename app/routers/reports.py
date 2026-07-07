import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission_codes import PermissionCode
from app.core.permissions import CurrentUser, get_company_scope, require_permission
from app.schemas.dashboard import CollaboratorBalanceSummary, DailyReportResponse
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
from app.services import dashboard_service, report_service

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

_require_view = require_permission(PermissionCode.REPORT_VIEW)
_require_export = require_permission(PermissionCode.REPORT_EXPORT)


def _csv_response(content: str, filename: str) -> PlainTextResponse:
    return PlainTextResponse(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/daily", response_model=DailyReportResponse)
async def get_daily_report(
    report_date: date = Query(default=None, alias="date"),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> DailyReportResponse:
    target_date = report_date or date.today()
    return await dashboard_service.build_daily_report(db, company_id, target_date)


@router.get("/daily/export", response_class=PlainTextResponse)
async def export_daily_report_csv(
    report_date: date = Query(default=None, alias="date"),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_export),
) -> PlainTextResponse:
    target_date = report_date or date.today()
    report = await dashboard_service.build_daily_report(db, company_id, target_date)
    csv_content = dashboard_service.daily_report_to_csv(report)
    return _csv_response(csv_content, f"rapport-{target_date.isoformat()}.csv")


@router.get("/monthly", response_model=MonthlyReportResponse)
async def get_monthly_report(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> MonthlyReportResponse:
    return await report_service.build_monthly_report(db, company_id, year, month)


@router.get("/monthly/export", response_class=PlainTextResponse)
async def export_monthly_report_csv(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_export),
) -> PlainTextResponse:
    report = await report_service.build_monthly_report(db, company_id, year, month)
    csv_content = report_service.monthly_report_to_csv(report)
    return _csv_response(csv_content, f"rapport-mensuel-{report.month}.csv")


@router.get("/transactions", response_model=list[TransactionReportRow])
async def get_transactions_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> list[TransactionReportRow]:
    return await report_service.build_transactions_report(db, company_id, date_from, date_to)


@router.get("/transactions/export", response_class=PlainTextResponse)
async def export_transactions_report_csv(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_export),
) -> PlainTextResponse:
    rows = await report_service.build_transactions_report(db, company_id, date_from, date_to)
    csv_content = report_service.rows_to_csv(rows, TransactionReportRow)
    return _csv_response(csv_content, "rapport-transactions.csv")


@router.get("/collaborator-balances", response_model=list[CollaboratorBalanceSummary])
async def get_collaborator_balances_report(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> list[CollaboratorBalanceSummary]:
    return await report_service.build_collaborator_balances_report(db, company_id)


@router.get("/collaborator-balances/export", response_class=PlainTextResponse)
async def export_collaborator_balances_report_csv(
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_export),
) -> PlainTextResponse:
    rows = await report_service.build_collaborator_balances_report(db, company_id)
    csv_content = report_service.rows_to_csv(rows, CollaboratorBalanceSummary)
    return _csv_response(csv_content, "rapport-soldes-collaborateurs.csv")


@router.get("/wallets/{wallet_id}/history", response_model=list[WalletMovementReportRow])
async def get_wallet_history_report(
    wallet_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> list[WalletMovementReportRow]:
    return await report_service.build_wallet_history_report(db, company_id, wallet_id, date_from, date_to)


@router.get("/wallets/{wallet_id}/history/export", response_class=PlainTextResponse)
async def export_wallet_history_report_csv(
    wallet_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_export),
) -> PlainTextResponse:
    rows = await report_service.build_wallet_history_report(db, company_id, wallet_id, date_from, date_to)
    csv_content = report_service.rows_to_csv(rows, WalletMovementReportRow)
    return _csv_response(csv_content, f"rapport-wallet-{wallet_id}.csv")


@router.get("/employees/{user_id}/activity", response_model=list[EmployeeActivityRow])
async def get_employee_activity_report(
    user_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> list[EmployeeActivityRow]:
    return await report_service.build_employee_activity_report(db, company_id, user_id, date_from, date_to)


@router.get("/employees/{user_id}/activity/export", response_class=PlainTextResponse)
async def export_employee_activity_report_csv(
    user_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_export),
) -> PlainTextResponse:
    rows = await report_service.build_employee_activity_report(db, company_id, user_id, date_from, date_to)
    csv_content = report_service.rows_to_csv(rows, EmployeeActivityRow)
    return _csv_response(csv_content, f"rapport-employe-{user_id}.csv")


@router.get("/suppliers", response_model=list[SupplierMovementReportRow])
async def get_suppliers_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> list[SupplierMovementReportRow]:
    return await report_service.build_supplier_report(db, company_id, date_from, date_to)


@router.get("/suppliers/export", response_class=PlainTextResponse)
async def export_suppliers_report_csv(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_export),
) -> PlainTextResponse:
    rows = await report_service.build_supplier_report(db, company_id, date_from, date_to)
    csv_content = report_service.rows_to_csv(rows, SupplierMovementReportRow)
    return _csv_response(csv_content, "rapport-fournisseurs.csv")


@router.get("/clients", response_model=list[ClientMovementReportRow])
async def get_clients_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> list[ClientMovementReportRow]:
    return await report_service.build_client_report(db, company_id, date_from, date_to)


@router.get("/clients/export", response_class=PlainTextResponse)
async def export_clients_report_csv(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_export),
) -> PlainTextResponse:
    rows = await report_service.build_client_report(db, company_id, date_from, date_to)
    csv_content = report_service.rows_to_csv(rows, ClientMovementReportRow)
    return _csv_response(csv_content, "rapport-clients.csv")


@router.get("/fees", response_model=list[FeeReportRow])
async def get_fees_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> list[FeeReportRow]:
    return await report_service.build_fees_report(db, company_id, date_from, date_to)


@router.get("/fees/export", response_class=PlainTextResponse)
async def export_fees_report_csv(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_export),
) -> PlainTextResponse:
    rows = await report_service.build_fees_report(db, company_id, date_from, date_to)
    csv_content = report_service.rows_to_csv(rows, FeeReportRow)
    return _csv_response(csv_content, "rapport-frais.csv")


@router.get("/rejected-operations", response_model=list[RejectedOperationReportRow])
async def get_rejected_operations_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_view),
) -> list[RejectedOperationReportRow]:
    return await report_service.build_rejected_operations_report(db, company_id, date_from, date_to)


@router.get("/rejected-operations/export", response_class=PlainTextResponse)
async def export_rejected_operations_report_csv(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_company_scope),
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(_require_export),
) -> PlainTextResponse:
    rows = await report_service.build_rejected_operations_report(db, company_id, date_from, date_to)
    csv_content = report_service.rows_to_csv(rows, RejectedOperationReportRow)
    return _csv_response(csv_content, "rapport-operations-rejetees.csv")
