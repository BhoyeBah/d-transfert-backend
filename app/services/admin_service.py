import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.company import Company, CompanyStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.repositories import (
    company_repository,
    entry_repository,
    national_operation_repository,
    payment_repository,
    platform_setting_repository,
    subscription_repository,
    system_log_repository,
    transfer_repository,
    user_repository,
    wallet_repository,
)
from app.schemas.admin import (
    AdminCompanyDetailResponse,
    AdminPlatformStatsResponse,
    AdminUserResponse,
    PlatformAdminCreateRequest,
    PlatformSettingsResponse,
    PlatformSettingsUpdateRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
    SystemLogResponse,
)
from app.schemas.company import AdminCompanyUpdateRequest
from app.services import audit_service
from app.utils.reference import generate_platform_admin_matricule


def _user_to_response(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        company_id=user.company_id,
        matricule=user.matricule,
        full_name=user.full_name,
        phone=user.phone,
        is_owner=user.is_owner,
        is_super_admin=user.is_super_admin,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _subscription_to_response(subscription: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        company_id=subscription.company_id,
        plan=subscription.plan,
        status=subscription.status,
        price=subscription.price,
        currency=subscription.currency,
        renews_at=subscription.renews_at,
    )


async def list_companies(session: AsyncSession) -> list[Company]:
    return await company_repository.list_all(session)


async def set_company_status(
    session: AsyncSession, acted_by_user_id: uuid.UUID, company_id: uuid.UUID, status: CompanyStatus
) -> Company:
    company = await company_repository.get_by_id(session, company_id)
    if company is None:
        raise NotFoundError("Entreprise introuvable.")

    company.status = status
    await audit_service.log_action(
        session, company.id, acted_by_user_id, "admin.company_status_change", "company", company.id,
        note=f"status={status.value}",
    )
    await session.commit()
    return company


async def update_company(
    session: AsyncSession,
    acted_by_user_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AdminCompanyUpdateRequest,
) -> Company:
    company = await company_repository.get_by_id(session, company_id)
    if company is None:
        raise NotFoundError("Entreprise introuvable.")

    if payload.phone is not None and payload.phone != company.phone:
        existing = await company_repository.get_by_phone(session, payload.phone)
        if existing is not None and existing.id != company.id:
            raise ConflictError("Ce numéro de téléphone est déjà utilisé par une autre entreprise.")
        company.phone = payload.phone
    if payload.name is not None:
        company.name = payload.name
    if payload.address is not None:
        company.address = payload.address
    if payload.default_currency is not None:
        company.default_currency = payload.default_currency

    await audit_service.log_action(
        session, company.id, acted_by_user_id, "admin.company_update", "company", company.id
    )
    await session.commit()
    return company


async def get_company_detail(session: AsyncSession, company_id: uuid.UUID) -> AdminCompanyDetailResponse:
    company = await company_repository.get_by_id(session, company_id)
    if company is None:
        raise NotFoundError("Entreprise introuvable.")

    users = await user_repository.list_all_by_company(session, company_id)
    wallets = await wallet_repository.list_by_company(session, company_id)
    balances: dict[str, Decimal] = defaultdict(Decimal)
    for wallet in wallets:
        balances[wallet.currency] += wallet.balance
    entries = await entry_repository.list_by_company(session, company_id)
    national_operations = await national_operation_repository.list_by_company(session, company_id)
    transfers = await transfer_repository.list_for_company(session, company_id)
    payments = await payment_repository.list_for_company(session, company_id)

    return AdminCompanyDetailResponse(
        id=company.id,
        name=company.name,
        registration_code=company.registration_code,
        address=company.address,
        phone=company.phone,
        default_currency=company.default_currency,
        status=company.status,
        created_at=company.created_at,
        users_count=len(users),
        wallets_count=len(wallets),
        wallets_balance_by_currency=dict(balances),
        entries_count=len(entries),
        national_operations_count=len(national_operations),
        transfers_count=len(transfers),
        payments_count=len(payments),
    )


async def list_company_users(session: AsyncSession, company_id: uuid.UUID) -> list[AdminUserResponse]:
    company = await company_repository.get_by_id(session, company_id)
    if company is None:
        raise NotFoundError("Entreprise introuvable.")

    users = await user_repository.list_all_by_company(session, company_id)
    return [_user_to_response(user) for user in users]


async def set_user_status(
    session: AsyncSession, acted_by_user_id: uuid.UUID, user_id: uuid.UUID, is_active: bool
) -> AdminUserResponse:
    user = await user_repository.get_by_id(session, user_id)
    if user is None:
        raise NotFoundError("Utilisateur introuvable.")

    if user.is_super_admin and not is_active:
        if user.id == acted_by_user_id:
            raise ConflictError("Vous ne pouvez pas suspendre votre propre compte.")
        if await user_repository.count_active_super_admins(session) <= 1:
            raise ConflictError("Impossible de suspendre le dernier compte Super Admin actif.")

    user.is_active = is_active
    await audit_service.log_action(
        session, user.company_id, acted_by_user_id, "admin.user_status_change", "user", user.id,
        note=f"is_active={is_active}",
    )
    await session.commit()
    return _user_to_response(user)


async def list_platform_admins(session: AsyncSession) -> list[AdminUserResponse]:
    admins = await user_repository.list_super_admins(session)
    return [_user_to_response(admin) for admin in admins]


async def create_platform_admin(
    session: AsyncSession, acted_by_user_id: uuid.UUID, payload: PlatformAdminCreateRequest
) -> AdminUserResponse:
    if await user_repository.get_super_admin_by_phone(session, payload.phone) is not None:
        raise ConflictError("Ce numéro de téléphone est déjà utilisé par un compte Super Admin.")

    matricule = None
    for _ in range(10):
        candidate = generate_platform_admin_matricule()
        if await user_repository.get_by_matricule(session, candidate) is None:
            matricule = candidate
            break
    if matricule is None:
        raise ConflictError("Impossible de générer un matricule unique, réessayez.")

    admin = User(
        company_id=None,
        matricule=matricule,
        full_name=payload.full_name,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        is_owner=False,
        is_super_admin=True,
        is_active=True,
    )
    session.add(admin)
    await session.flush()
    await audit_service.log_action(
        session, None, acted_by_user_id, "admin.platform_admin_create", "user", admin.id
    )
    await session.commit()
    return _user_to_response(admin)


async def get_platform_stats(session: AsyncSession) -> AdminPlatformStatsResponse:
    status_counts = await company_repository.count_by_status(session)
    users_total = await user_repository.count_all(session)
    wallets_total = await wallet_repository.count_all(session)
    entries_total = await entry_repository.count_all(session)
    national_operations_total = await national_operation_repository.count_all(session)
    transfers_total = await transfer_repository.count_all(session)
    payments_total = await payment_repository.count_all(session)

    volume_by_currency: dict[str, Decimal] = defaultdict(Decimal)
    for currency, amount in (await transfer_repository.sum_amount_by_currency(session)).items():
        volume_by_currency[currency] += amount
    for currency, amount in (await payment_repository.sum_amount_by_currency(session)).items():
        volume_by_currency[currency] += amount

    recent_logs = await system_log_repository.list_recent(session, limit=500)

    return AdminPlatformStatsResponse(
        companies_total=sum(status_counts.values()),
        companies_active=status_counts.get(CompanyStatus.ACTIVE, 0),
        companies_pending=status_counts.get(CompanyStatus.PENDING, 0),
        companies_suspended=status_counts.get(CompanyStatus.SUSPENDED, 0),
        users_total=users_total,
        wallets_total=wallets_total,
        entries_total=entries_total,
        national_operations_total=national_operations_total,
        transfers_total=transfers_total,
        payments_total=payments_total,
        transactions_total=entries_total + national_operations_total + transfers_total + payments_total,
        volume_by_currency=dict(volume_by_currency),
        system_logs_recent_count=len(recent_logs),
    )


async def list_system_logs(session: AsyncSession) -> list[SystemLogResponse]:
    logs = await system_log_repository.list_recent(session, limit=500)
    return [
        SystemLogResponse(
            id=log.id,
            level=log.level,
            source=log.source,
            message=log.message,
            company_id=log.company_id,
            user_id=log.user_id,
            created_at=log.created_at,
        )
        for log in logs
    ]


async def get_settings(session: AsyncSession) -> PlatformSettingsResponse:
    setting = await platform_setting_repository.get(session)
    if setting is None:
        setting = await platform_setting_repository.create_default(session)
        await session.commit()
    return PlatformSettingsResponse(
        supported_currencies=setting.supported_currencies,
        max_transaction_amount=setting.max_transaction_amount,
        maintenance_mode=setting.maintenance_mode,
    )


async def update_settings(
    session: AsyncSession, acted_by_user_id: uuid.UUID, payload: PlatformSettingsUpdateRequest
) -> PlatformSettingsResponse:
    setting = await platform_setting_repository.get(session)
    if setting is None:
        setting = await platform_setting_repository.create_default(session)

    if payload.supported_currencies is not None:
        setting.supported_currencies = payload.supported_currencies
    if payload.max_transaction_amount is not None:
        setting.max_transaction_amount = payload.max_transaction_amount
    if payload.maintenance_mode is not None:
        setting.maintenance_mode = payload.maintenance_mode

    await audit_service.log_action(
        session, None, acted_by_user_id, "admin.settings_update", "platform_setting", setting.id
    )
    await session.commit()
    return PlatformSettingsResponse(
        supported_currencies=setting.supported_currencies,
        max_transaction_amount=setting.max_transaction_amount,
        maintenance_mode=setting.maintenance_mode,
    )


async def get_subscription(session: AsyncSession, company_id: uuid.UUID) -> SubscriptionResponse:
    company = await company_repository.get_by_id(session, company_id)
    if company is None:
        raise NotFoundError("Entreprise introuvable.")

    subscription = await subscription_repository.get_by_company(session, company_id)
    if subscription is None:
        subscription = await subscription_repository.create_default(session, company_id)
        await session.commit()
    return _subscription_to_response(subscription)


async def update_subscription(
    session: AsyncSession,
    acted_by_user_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: SubscriptionUpdateRequest,
) -> SubscriptionResponse:
    company = await company_repository.get_by_id(session, company_id)
    if company is None:
        raise NotFoundError("Entreprise introuvable.")

    subscription = await subscription_repository.get_by_company(session, company_id)
    if subscription is None:
        subscription = await subscription_repository.create_default(session, company_id)

    if payload.plan is not None:
        subscription.plan = payload.plan
    if payload.status is not None:
        subscription.status = payload.status
    if payload.price is not None:
        subscription.price = payload.price
    if payload.currency is not None:
        subscription.currency = payload.currency
    if payload.renews_at is not None:
        subscription.renews_at = payload.renews_at

    await audit_service.log_action(
        session, company_id, acted_by_user_id, "admin.subscription_update", "subscription", subscription.id
    )
    await session.commit()
    return _subscription_to_response(subscription)
