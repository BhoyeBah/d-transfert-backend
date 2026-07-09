import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import OverrideEffect, Permission, RolePermission, UserPermissionOverride
from app.models.user import User
from app.utils.pagination import paginate

_SORTABLE_COLUMNS = {
    "full_name": User.full_name,
    "created_at": User.created_at,
}

_SUPER_ADMIN_SORTABLE_COLUMNS = {
    "full_name": User.full_name,
    "phone": User.phone,
    "created_at": User.created_at,
}


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


async def get_by_matricule(session: AsyncSession, matricule: str) -> User | None:
    result = await session.execute(select(User).where(User.matricule == matricule))
    return result.scalar_one_or_none()


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


async def list_by_company_page(
    session: AsyncSession,
    company_id: uuid.UUID,
    page: int,
    page_size: int,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> tuple[list[User], int]:
    stmt = select(User).where(User.company_id == company_id, User.is_owner.is_(False))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(User.full_name.ilike(pattern), User.phone.ilike(pattern), User.matricule.ilike(pattern))
        )
    column = _SORTABLE_COLUMNS.get(sort_by, User.created_at)
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    return await paginate(session, stmt, page, page_size)


async def count_employees_by_company(session: AsyncSession, company_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.count()).select_from(User).where(
            User.company_id == company_id, User.is_owner.is_(False)
        )
    )
    return int(result.scalar_one())


async def list_all_by_company(session: AsyncSession, company_id: uuid.UUID) -> list[User]:
    """Owner and employees, for platform administration (unlike list_by_company)."""
    result = await session.execute(
        select(User).where(User.company_id == company_id).order_by(User.is_owner.desc(), User.created_at)
    )
    return list(result.scalars().all())


async def count_all(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(User))
    return int(result.scalar_one())


async def list_super_admins(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).where(User.is_super_admin.is_(True)).order_by(User.created_at)
    )
    return list(result.scalars().all())


async def list_super_admins_page(
    session: AsyncSession,
    page: int,
    page_size: int,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> tuple[list[User], int]:
    stmt = select(User).where(User.is_super_admin.is_(True))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(User.full_name.ilike(pattern), User.phone.ilike(pattern), User.matricule.ilike(pattern))
        )
    column = _SUPER_ADMIN_SORTABLE_COLUMNS.get(sort_by, User.created_at)
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    return await paginate(session, stmt, page, page_size)


async def get_super_admin_by_phone(session: AsyncSession, phone: str) -> User | None:
    result = await session.execute(
        select(User).where(User.is_super_admin.is_(True), User.phone == phone)
    )
    return result.scalar_one_or_none()


async def count_active_super_admins(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count()).select_from(User).where(
            User.is_super_admin.is_(True), User.is_active.is_(True)
        )
    )
    return int(result.scalar_one())


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
