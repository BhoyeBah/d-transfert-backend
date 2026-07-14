import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.security import TokenType, decode_token
from app.models.company import CompanyStatus
from app.core.permission_codes import PermissionCode
from app.repositories import company_repository, revoked_token_repository, user_repository


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    company_id: uuid.UUID | None
    permissions: frozenset[str]
    is_owner: bool = False
    is_super_admin: bool = False


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Token d'authentification manquant.")

    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token, TokenType.ACCESS)

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Token invalide.") from exc

    if await revoked_token_repository.is_revoked(db, payload["jti"]):
        raise UnauthorizedError("Session terminée, reconnectez-vous.")

    user = await user_repository.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Compte introuvable ou désactivé.")

    if user.password_changed_at is not None and payload["iat"] < user.password_changed_at.timestamp():
        raise UnauthorizedError("Session terminée suite à un changement de mot de passe, reconnectez-vous.")

    if user.company_id is not None:
        company = await company_repository.get_by_id(db, user.company_id)
        if company is None or company.status == CompanyStatus.SUSPENDED:
            raise UnauthorizedError("Entreprise suspendue.")

    if user.is_owner or user.is_super_admin:
        permissions: frozenset[str] = frozenset(code.value for code in PermissionCode)
    else:
        permissions = await user_repository.get_effective_permission_codes(db, user)

    return CurrentUser(
        id=user.id,
        company_id=user.company_id,
        permissions=permissions,
        is_owner=user.is_owner,
        is_super_admin=user.is_super_admin,
    )


def require_permission(permission_code: str) -> Callable[..., CurrentUser]:
    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.is_super_admin or current_user.is_owner:
            return current_user
        if permission_code not in current_user.permissions:
            raise PermissionDeniedError(f"Permission requise : {permission_code}")
        return current_user

    return dependency


def require_any_permission(*permission_codes: str) -> Callable[..., CurrentUser]:
    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.is_super_admin or current_user.is_owner:
            return current_user
        if not any(code in current_user.permissions for code in permission_codes):
            required = ", ".join(permission_codes)
            raise PermissionDeniedError(f"Une des permissions suivantes est requise : {required}")
        return current_user

    return dependency


def get_company_scope(current_user: CurrentUser = Depends(get_current_user)) -> uuid.UUID:
    if current_user.company_id is None:
        raise PermissionDeniedError("Aucune entreprise associée à cet utilisateur.")
    return current_user.company_id
