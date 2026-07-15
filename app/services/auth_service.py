import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.company import CompanyStatus
from app.models.system_log import SystemLogLevel
from app.models.user import User
from app.repositories import (
    company_repository,
    password_reset_otp_repository,
    platform_setting_repository,
    revoked_token_repository,
    user_repository,
)
from app.schemas.auth import RegisterRequest, RegisterResponse
from app.services import audit_service, system_log_service
from app.services.company_service import create_company_with_owner
logger = logging.getLogger("dtransfert.auth")

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
OTP_EXPIRE_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
async def register(db: AsyncSession, payload: RegisterRequest) -> RegisterResponse:
    platform_setting = await platform_setting_repository.get(db)
    if platform_setting is not None and platform_setting.maintenance_mode:
        raise UnauthorizedError("La plateforme est en mode maintenance.")
    require_approval = platform_setting is not None and platform_setting.require_company_approval
    company, owner = await create_company_with_owner(
        db,
        company_name=payload.company_name,
        company_phone=payload.company_phone,
        address=payload.address,
        default_currency=payload.default_currency,
        owner_full_name=payload.owner_full_name,
        password=payload.password,
        status=CompanyStatus.PENDING if require_approval else CompanyStatus.ACTIVE,
    )
    await db.commit()

    return RegisterResponse(
        company_id=company.id, registration_code=company.registration_code, owner_user_id=owner.id
    )


async def _find_login_user(db: AsyncSession, matricule: str) -> User:
    user = await user_repository.get_by_matricule(db, matricule)
    if user is None:
        raise UnauthorizedError("Identifiants invalides.")
    return user


def _is_locked(user: User) -> bool:
    return user.locked_until is not None and user.locked_until > datetime.now(timezone.utc)


async def _ensure_company_active(db: AsyncSession, user: User) -> None:
    if user.is_super_admin:
        return
    if user.company_id is None:
        raise UnauthorizedError("Compte introuvable ou désactivé.")
    company = await company_repository.get_by_id(db, user.company_id)
    if company is None or company.status == CompanyStatus.SUSPENDED:
        raise UnauthorizedError("Entreprise suspendue.")
    if company.status == CompanyStatus.PENDING:
        raise UnauthorizedError(
            "Votre entreprise est en attente de validation par la plateforme. Réessayez plus tard."
        )


async def login(db: AsyncSession, matricule: str, password: str) -> tuple[str, str]:
    user = await _find_login_user(db, matricule)
    platform_setting = await platform_setting_repository.get(db)
    if platform_setting is not None and platform_setting.maintenance_mode and not user.is_super_admin:
        raise UnauthorizedError("La plateforme est en mode maintenance.")

    if not user.is_super_admin:
        await _ensure_company_active(db, user)

    if _is_locked(user):
        await system_log_service.log(
            db, SystemLogLevel.WARNING, "auth", f"Tentative de connexion sur un compte verrouillé (matricule={matricule}).",
            company_id=user.company_id, user_id=user.id,
        )
        await db.commit()
        raise UnauthorizedError("Compte temporairement verrouillé suite à plusieurs échecs. Réessayez plus tard.")

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            await system_log_service.log(
                db, SystemLogLevel.WARNING, "auth", f"Compte verrouillé après échecs répétés (matricule={matricule}).",
                company_id=user.company_id, user_id=user.id,
            )
        else:
            await system_log_service.log(
                db, SystemLogLevel.WARNING, "auth", f"Échec de connexion (matricule={matricule}).",
                company_id=user.company_id, user_id=user.id,
            )
        await db.commit()
        raise UnauthorizedError("Identifiants invalides.")

    if not user.is_active:
        raise UnauthorizedError("Compte désactivé.")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    await audit_service.log_action(db, user.company_id, user.id, "login", "user", user.id)
    await db.commit()

    company_id = str(user.company_id) if user.company_id else None
    return (
        create_access_token(
            str(user.id),
            company_id,
            matricule=user.matricule,
            is_owner=user.is_owner,
            is_super_admin=user.is_super_admin,
        ),
        create_refresh_token(
            str(user.id),
            company_id,
            matricule=user.matricule,
            is_owner=user.is_owner,
            is_super_admin=user.is_super_admin,
        ),
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
    payload = decode_token(refresh_token, TokenType.REFRESH)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Token invalide.") from exc

    if await revoked_token_repository.is_revoked(db, payload["jti"]):
        raise UnauthorizedError("Session terminée, reconnectez-vous.")

    user = await user_repository.get_by_id(db, user_id)
    if user is None or not user.is_active or _is_locked(user):
        raise UnauthorizedError("Compte introuvable, désactivé ou verrouillé.")

    if user.password_changed_at is not None and payload["iat"] < user.password_changed_at.timestamp():
        raise UnauthorizedError("Session terminée suite à un changement de mot de passe, reconnectez-vous.")

    if not user.is_super_admin:
        await _ensure_company_active(db, user)

    company_id = str(user.company_id) if user.company_id else None
    return (
        create_access_token(
            str(user.id),
            company_id,
            matricule=user.matricule,
            is_owner=user.is_owner,
            is_super_admin=user.is_super_admin,
        ),
        create_refresh_token(
            str(user.id),
            company_id,
            matricule=user.matricule,
            is_owner=user.is_owner,
            is_super_admin=user.is_super_admin,
        ),
    )


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def request_password_reset(db: AsyncSession, matricule: str) -> None:
    user = await user_repository.get_by_matricule(db, matricule)
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
    otp_code: str,
    new_password: str,
) -> None:
    user = await user_repository.get_by_matricule(db, matricule)
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
    # Invalide d'un coup toutes les sessions déjà émises (access et refresh tokens) : leur
    # `iat` est forcément antérieur à cet instant, cf. la vérification dans
    # app/core/permissions.py et refresh_tokens ci-dessus.
    user.password_changed_at = datetime.now(timezone.utc)
    await db.commit()


async def logout(db: AsyncSession, access_token: str, refresh_token: str | None) -> None:
    access_payload = decode_token(access_token, TokenType.ACCESS)
    await revoked_token_repository.revoke(
        db, access_payload["jti"], datetime.fromtimestamp(access_payload["exp"], tz=timezone.utc)
    )

    if refresh_token is not None:
        try:
            refresh_payload = decode_token(refresh_token, TokenType.REFRESH)
        except UnauthorizedError:
            # Refresh token déjà expiré/invalide : rien de plus à révoquer.
            pass
        else:
            await revoked_token_repository.revoke(
                db, refresh_payload["jti"], datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
            )

    await db.commit()
