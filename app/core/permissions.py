from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header

from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.security import TokenType, decode_token


@dataclass(frozen=True)
class CurrentUser:
    id: str
    company_id: str | None
    permissions: frozenset[str]
    is_super_admin: bool = False


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Token d'authentification manquant.")

    token = authorization.removeprefix("Bearer ")
    decode_token(token, TokenType.ACCESS)

    # Chargement réel de l'utilisateur (rôle, permissions effectives) branché en Phase 2
    # une fois les modèles User/Role/Permission/UserPermissionOverride disponibles.
    raise NotImplementedError("get_current_user sera complété en Phase 2.")


def require_permission(permission_code: str) -> Callable[..., CurrentUser]:
    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.is_super_admin:
            return current_user
        if permission_code not in current_user.permissions:
            raise PermissionDeniedError(f"Permission requise : {permission_code}")
        return current_user

    return dependency


def get_company_scope(current_user: CurrentUser = Depends(get_current_user)) -> str:
    if current_user.company_id is None:
        raise PermissionDeniedError("Aucune entreprise associée à cet utilisateur.")
    return current_user.company_id
