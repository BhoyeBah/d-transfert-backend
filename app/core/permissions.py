import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.security import TokenType, decode_token
from app.models.company import CompanyStatus
from app.repositories import company_repository, user_repository


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

    user = await user_repository.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Compte introuvable ou désactivé.")

    if user.company_id is not None:
        company = await company_repository.get_by_id(db, user.company_id)
        if company is None or company.status == CompanyStatus.SUSPENDED:
            raise UnauthorizedError("Entreprise suspendue.")

    if user.is_owner or user.is_super_admin:
        permissions: frozenset[str] = frozenset()
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


def get_company_scope(current_user: CurrentUser = Depends(get_current_user)) -> uuid.UUID:
    if current_user.company_id is None:
        raise PermissionDeniedError("Aucune entreprise associée à cet utilisateur.")
    return current_user.company_id
