import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import OverrideEffect, Permission, RolePermission, UserPermissionOverride
from app.models.user import User


async def get_by_company_and_id(session: AsyncSession, company_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
    result = await session.execute(
        select(User).where(User.company_id == company_id, User.id == user_id, User.is_owner.is_(False))
    )
    return result.scalar_one_or_none()


async def set_permission_override(
    session: AsyncSession, user_id: uuid.UUID, permission_id: uuid.UUID, effect: OverrideEffect
) -> None:
    result = await session.execute(
        select(UserPermissionOverride).where(
            UserPermissionOverride.user_id == user_id,
            UserPermissionOverride.permission_id == permission_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.effect = effect
    else:
        session.add(
            UserPermissionOverride(user_id=user_id, permission_id=permission_id, effect=effect)
        )


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_by_company_and_phone(
    session: AsyncSession, company_id: uuid.UUID, phone: str
) -> User | None:
    result = await session.execute(
        select(User).where(User.company_id == company_id, User.phone == phone)
    )
    return result.scalar_one_or_none()


async def get_owner_by_company(session: AsyncSession, company_id: uuid.UUID) -> User | None:
    result = await session.execute(
        select(User).where(User.company_id == company_id, User.is_owner.is_(True))
    )
    return result.scalar_one_or_none()


async def list_by_company(session: AsyncSession, company_id: uuid.UUID) -> list[User]:
    result = await session.execute(
        select(User).where(User.company_id == company_id, User.is_owner.is_(False))
    )
    return list(result.scalars().all())


async def get_effective_permission_codes(session: AsyncSession, user: User) -> frozenset[str]:
    role_codes: set[str] = set()
    if user.role_id is not None:
        result = await session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == user.role_id)
        )
        role_codes = set(result.scalars().all())

    overrides_result = await session.execute(
        select(Permission.code, UserPermissionOverride.effect)
        .join(Permission, Permission.id == UserPermissionOverride.permission_id)
        .where(UserPermissionOverride.user_id == user.id)
    )
    for code, effect in overrides_result.all():
        if effect == OverrideEffect.GRANT:
            role_codes.add(code)
        else:
            role_codes.discard(code)

    return frozenset(role_codes)
