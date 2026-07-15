import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.company import CompanyStatus
from app.models.subscription import SubscriptionPlan, SubscriptionStatus
from app.models.system_log import SystemLogLevel


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID | None
    matricule: str
    full_name: str
    phone: str
    is_owner: bool
    is_super_admin: bool
    is_active: bool
    created_at: datetime


class AdminUserStatusUpdateRequest(BaseModel):
    is_active: bool


class AdminUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=6, max_length=32)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class PlatformAdminCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=6, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class AdminCompanyDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    registration_code: str
    address: str | None
    phone: str
    default_currency: str
    status: CompanyStatus
    created_at: datetime
    users_count: int
    wallets_count: int
    wallets_balance_by_currency: dict[str, Decimal]
    entries_count: int
    national_operations_count: int
    transfers_count: int
    payments_count: int


class AdminPlatformStatsResponse(BaseModel):
    companies_total: int
    companies_active: int
    companies_pending: int
    companies_suspended: int
    users_total: int
    wallets_total: int
    entries_total: int
    national_operations_total: int
    transfers_total: int
    payments_total: int
    transactions_total: int
    volume_by_currency: dict[str, Decimal]
    system_logs_recent_count: int


class SystemLogResponse(BaseModel):
    id: uuid.UUID
    level: SystemLogLevel
    source: str
    message: str
    company_id: uuid.UUID | None
    user_id: uuid.UUID | None
    created_at: datetime


class PlatformSettingsResponse(BaseModel):
    supported_currencies: list[str]
    max_transaction_amount: Decimal | None
    maintenance_mode: bool
    require_company_approval: bool


class PlatformSettingsUpdateRequest(BaseModel):
    supported_currencies: list[str] | None = None
    max_transaction_amount: Decimal | None = None
    maintenance_mode: bool | None = None
    require_company_approval: bool | None = None


class AdminBackupResponse(BaseModel):
    filename: str
    created_at: datetime
    size_bytes: int


class AdminBackupActionResponse(BaseModel):
    detail: str
    backup: AdminBackupResponse


class AdminBackupRestoreRequest(BaseModel):
    filename: str = Field(pattern=r"^dtransfert_\d{8}_\d{6}\.dump\.gz$")


class SubscriptionResponse(BaseModel):
    company_id: uuid.UUID
    plan: SubscriptionPlan
    status: SubscriptionStatus
    price: Decimal | None
    currency: str | None
    renews_at: datetime | None


class SubscriptionUpdateRequest(BaseModel):
    plan: SubscriptionPlan | None = None
    status: SubscriptionStatus | None = None
    price: Decimal | None = None
    currency: str | None = None
    renews_at: datetime | None = None
