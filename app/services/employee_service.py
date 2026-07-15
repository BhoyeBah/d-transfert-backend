import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permission_codes import PermissionCode, RoleCode
from app.core.security import hash_password
from app.models.role import OverrideEffect
from app.models.user import User
from app.repositories import role_repository, user_repository
from app.schemas.employee import EmployeeCreateRequest, EmployeeResponse
from app.schemas.pagination import PageParams
from app.services import audit_service
from app.services.user_management_service import count_user_dependency_usage, has_user_dependencies
from app.utils.reference import generate_employee_matricule


async def _to_response(db: AsyncSession, user: User) -> EmployeeResponse:
    permissions = await user_repository.get_effective_permission_codes(db, user)
    return EmployeeResponse(
        id=user.id,
        matricule=user.matricule,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        permissions=sorted(PermissionCode(code) for code in permissions),
        created_at=user.created_at,
    )


async def create_employee(
    db: AsyncSession, company_id: uuid.UUID, acted_by_user_id: uuid.UUID, payload: EmployeeCreateRequest
) -> EmployeeResponse:
    if await user_repository.get_by_company_and_phone(db, company_id, payload.phone) is not None:
        raise ConflictError("Ce numéro de téléphone est déjà utilisé dans cette entreprise.")

    employee_role = await role_repository.get_role_by_code(db, RoleCode.EMPLOYEE)
    if employee_role is None:
        raise ConflictError("Rôle employé introuvable, seed de rôles manquant.")

    owner = await user_repository.get_owner_by_company(db, company_id)
    if owner is None:
        raise ConflictError("Entreprise introuvable ou sans owner.")

    next_sequence = await user_repository.count_employees_by_company(db, company_id) + 1
    matricule = None
    for _ in range(10):
        candidate = generate_employee_matricule(owner.matricule, next_sequence)
        if await user_repository.get_by_matricule(db, candidate) is None:
            matricule = candidate
            break
        next_sequence += 1
    if matricule is None:
        raise ConflictError("Impossible de générer un matricule employé unique, réessayez.")

    user = User(
        company_id=company_id,
        role_id=employee_role.id,
        matricule=matricule,
        full_name=payload.full_name,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        is_owner=False,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    for code in payload.permissions:
        permission = await role_repository.get_permission_by_code(db, code)
        if permission is None:
            continue
        await user_repository.set_permission_override(db, user.id, permission.id, OverrideEffect.GRANT)

    await audit_service.log_action(db, company_id, acted_by_user_id, "employee.create", "user", user.id)
    await db.commit()
    return await _to_response(db, user)


async def list_employees(db: AsyncSession, company_id: uuid.UUID) -> list[EmployeeResponse]:
    users = await user_repository.list_by_company(db, company_id)
    return [await _to_response(db, user) for user in users]


async def list_employees_page(
    db: AsyncSession, company_id: uuid.UUID, params: PageParams
) -> tuple[list[EmployeeResponse], int]:
    users, total = await user_repository.list_by_company_page(
        db, company_id, params.page, params.page_size, params.search, params.sort_by, params.sort_dir
    )
    return [await _to_response(db, user) for user in users], total


async def update_permissions(
    db: AsyncSession,
    company_id: uuid.UUID,
    acted_by_user_id: uuid.UUID,
    employee_id: uuid.UUID,
    grant: list[PermissionCode],
    revoke: list[PermissionCode],
) -> EmployeeResponse:
    user = await user_repository.get_by_company_and_id(db, company_id, employee_id)
    if user is None:
        raise NotFoundError("Employé introuvable.")

    for code in grant:
        permission = await role_repository.get_permission_by_code(db, code)
        if permission is None:
            continue
        await user_repository.set_permission_override(db, user.id, permission.id, OverrideEffect.GRANT)

    for code in revoke:
        permission = await role_repository.get_permission_by_code(db, code)
        if permission is None:
            continue
        await user_repository.set_permission_override(db, user.id, permission.id, OverrideEffect.REVOKE)

    await audit_service.log_action(
        db,
        company_id,
        acted_by_user_id,
        "employee.permission_change",
        "user",
        user.id,
        note=f"grant={[c.value for c in grant]} revoke={[c.value for c in revoke]}",
    )
    await db.commit()
    return await _to_response(db, user)


async def set_active_status(
    db: AsyncSession, company_id: uuid.UUID, acted_by_user_id: uuid.UUID, employee_id: uuid.UUID, is_active: bool
) -> EmployeeResponse:
    user = await user_repository.get_by_company_and_id(db, company_id, employee_id)
    if user is None:
        raise NotFoundError("Employé introuvable.")

    user.is_active = is_active
    await audit_service.log_action(
        db, company_id, acted_by_user_id, "employee.status_change", "user", user.id,
        note=f"is_active={is_active}",
    )
    await db.commit()
    return await _to_response(db, user)


async def update_employee(
    db: AsyncSession,
    company_id: uuid.UUID,
    acted_by_user_id: uuid.UUID,
    employee_id: uuid.UUID,
    full_name: str | None = None,
    phone: str | None = None,
    password: str | None = None,
) -> EmployeeResponse:
    user = await user_repository.get_by_company_and_id(db, company_id, employee_id)
    if user is None:
        raise NotFoundError("Employé introuvable.")

    if phone is not None and phone != user.phone:
        existing = await user_repository.get_by_company_and_phone(db, company_id, phone)
        if existing is not None and existing.id != user.id:
            raise ConflictError("Ce numéro de téléphone est déjà utilisé dans cette entreprise.")
        user.phone = phone
    if full_name is not None:
        user.full_name = full_name
    if password is not None:
        user.password_hash = hash_password(password)

    await audit_service.log_action(
        db, company_id, acted_by_user_id, "employee.update", "user", user.id,
        note=f"full_name={full_name!r} phone={phone!r} password={'yes' if password else 'no'}",
    )
    await db.commit()
    return await _to_response(db, user)


async def delete_employee(
    db: AsyncSession, company_id: uuid.UUID, acted_by_user_id: uuid.UUID, employee_id: uuid.UUID
) -> None:
    user = await user_repository.get_by_company_and_id(db, company_id, employee_id)
    if user is None:
        raise NotFoundError("Employé introuvable.")

    counts = await count_user_dependency_usage(db, user.id)
    if has_user_dependencies(counts):
        raise ConflictError(
            "Cet utilisateur ne peut pas être supprimé car il est référencé par des données métier. "
            "Désactivez le compte à la place."
        )

    await audit_service.log_action(
        db, company_id, acted_by_user_id, "employee.delete", "user", user.id
    )
    await db.delete(user)
    await db.commit()


async def get_employee_activity(
    db: AsyncSession, company_id: uuid.UUID, employee_id: uuid.UUID
) -> list:
    user = await user_repository.get_by_company_and_id(db, company_id, employee_id)
    if user is None:
        raise NotFoundError("Employé introuvable.")
    return await audit_service.list_for_employee(db, company_id, employee_id)
