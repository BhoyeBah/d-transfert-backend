import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission, Role, RolePermission


async def get_role_by_code(session: AsyncSession, code: str) -> Role | None:
    result = await session.execute(select(Role).where(Role.code == code))
    return result.scalar_one_or_none()


async def get_permission_by_code(session: AsyncSession, code: str) -> Permission | None:
    result = await session.execute(select(Permission).where(Permission.code == code))
    return result.scalar_one_or_none()


async def get_permissions_by_codes(session: AsyncSession, codes: list[str]) -> list[Permission]:
    if not codes:
        return []
    result = await session.execute(select(Permission).where(Permission.code.in_(codes)))
    return list(result.scalars().all())


async def get_role_permission_codes(session: AsyncSession, role_id: uuid.UUID) -> frozenset[str]:
    result = await session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    )
    return frozenset(result.scalars().all())
