import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.company import Company, CompanyStatus
from app.models.user import User
from app.repositories import company_repository, password_reset_otp_repository, user_repository
from app.schemas.auth import RegisterRequest, RegisterResponse
from app.utils.reference import generate_company_registration_code

logger = logging.getLogger("dtransfert.auth")

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
OTP_EXPIRE_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
REGISTRATION_CODE_MAX_RETRIES = 5


async def register(db: AsyncSession, payload: RegisterRequest) -> RegisterResponse:
    if await company_repository.get_by_phone(db, payload.company_phone) is not None:
        raise ConflictError("Ce numéro de téléphone est déjà utilisé par une entreprise.")

    registration_code = None
    for _ in range(REGISTRATION_CODE_MAX_RETRIES):
        candidate = generate_company_registration_code()
        if await company_repository.get_by_registration_code(db, candidate) is None:
            registration_code = candidate
            break
    if registration_code is None:
        raise ConflictError("Impossible de générer un matricule unique, réessayez.")

    company = Company(
        name=payload.company_name,
        registration_code=registration_code,
        address=payload.address,
        phone=payload.company_phone,
        default_currency=payload.default_currency,
        status=CompanyStatus.ACTIVE,
    )
    db.add(company)
    await db.flush()

    owner = User(
        company_id=company.id,
        full_name=payload.owner_full_name,
        phone=payload.company_phone,
        password_hash=hash_password(payload.password),
        is_owner=True,
        is_active=True,
    )
    db.add(owner)
    await db.flush()
    await db.commit()

    return RegisterResponse(
        company_id=company.id, registration_code=company.registration_code, owner_user_id=owner.id
    )


async def _find_login_user(db: AsyncSession, matricule: str, phone: str | None) -> tuple[Company, User]:
    company = await company_repository.get_by_registration_code(db, matricule)
    if company is None:
        raise UnauthorizedError("Identifiants invalides.")

    if phone:
        user = await user_repository.get_by_company_and_phone(db, company.id, phone)
    else:
        user = await user_repository.get_owner_by_company(db, company.id)

    if user is None:
        raise UnauthorizedError("Identifiants invalides.")

    return company, user


def _is_locked(user: User) -> bool:
    return user.locked_until is not None and user.locked_until > datetime.now(timezone.utc)


async def login(db: AsyncSession, matricule: str, phone: str | None, password: str) -> tuple[str, str]:
    company, user = await _find_login_user(db, matricule, phone)

    if company.status == CompanyStatus.SUSPENDED:
        raise UnauthorizedError("Entreprise suspendue.")

    if _is_locked(user):
        raise UnauthorizedError("Compte temporairement verrouillé suite à plusieurs échecs. Réessayez plus tard.")

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        await db.commit()
        raise UnauthorizedError("Identifiants invalides.")

    if not user.is_active:
        raise UnauthorizedError("Compte désactivé.")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    company_id = str(user.company_id) if user.company_id else None
    return create_access_token(str(user.id), company_id), create_refresh_token(str(user.id), company_id)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
    payload = decode_token(refresh_token, TokenType.REFRESH)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Token invalide.") from exc

    user = await user_repository.get_by_id(db, user_id)
    if user is None or not user.is_active or _is_locked(user):
        raise UnauthorizedError("Compte introuvable, désactivé ou verrouillé.")

    company_id = str(user.company_id) if user.company_id else None
    return create_access_token(str(user.id), company_id), create_refresh_token(str(user.id), company_id)


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def request_password_reset(db: AsyncSession, matricule: str, phone: str | None) -> None:
    company = await company_repository.get_by_registration_code(db, matricule)
    if company is None:
        return

    if phone:
        user = await user_repository.get_by_company_and_phone(db, company.id, phone)
    else:
        user = await user_repository.get_owner_by_company(db, company.id)

    if user is None:
        return

    code = _generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    await password_reset_otp_repository.create(db, user.id, hash_password(code), expires_at)
    await db.commit()

    # Canal SMS/WhatsApp réel à brancher en phase notifications (Phase 10).
    logger.info("OTP de réinitialisation généré pour user_id=%s: %s", user.id, code)


async def reset_password(
    db: AsyncSession,
    matricule: str,
    phone: str | None,
    otp_code: str,
    new_password: str,
) -> None:
    company = await company_repository.get_by_registration_code(db, matricule)
    if company is None:
        raise UnauthorizedError("Identifiants invalides.")

    if phone:
        user = await user_repository.get_by_company_and_phone(db, company.id, phone)
    else:
        user = await user_repository.get_owner_by_company(db, company.id)

    if user is None:
        raise UnauthorizedError("Identifiants invalides.")

    otp = await password_reset_otp_repository.get_latest_unused(db, user.id)
    if otp is None or otp.attempts >= OTP_MAX_ATTEMPTS or otp.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedError("Code OTP invalide ou expiré.")

    if not verify_password(otp_code, otp.code_hash):
        otp.attempts += 1
        await db.commit()
        raise UnauthorizedError("Code OTP invalide ou expiré.")

    otp.used_at = datetime.now(timezone.utc)
    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()
