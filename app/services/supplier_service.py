import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.supplier import Supplier
from app.models.supplier_balance_movement import SupplierBalanceMovement, SupplierMovementType
from app.models.wallet_movement import MovementDirection
from app.repositories import supplier_repository, wallet_repository
from app.schemas.supplier import SupplierCreateRequest, SupplierRebalanceRequest
from app.services import wallet_service
from app.utils.reference import generate_supplier_movement_reference

REFERENCE_MAX_RETRIES = 5
_CENTS = Decimal("0.01")


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


async def _generate_unique_reference(session: AsyncSession) -> str:
    for _ in range(REFERENCE_MAX_RETRIES):
        candidate = generate_supplier_movement_reference()
        if await supplier_repository.get_by_reference(session, candidate) is None:
            return candidate
    raise ConflictError("Impossible de générer une référence unique, réessayez.")


async def create_supplier(
    session: AsyncSession, company_id: uuid.UUID, payload: SupplierCreateRequest
) -> Supplier:
    if await supplier_repository.get_by_company_and_code(session, company_id, payload.code) is not None:
        raise ConflictError("Ce code fournisseur est déjà utilisé dans cette entreprise.")

    supplier = Supplier(
        company_id=company_id,
        name=payload.name,
        code=payload.code,
        phone=payload.phone,
        address=payload.address,
        currency=payload.currency,
        note=payload.note,
        balance=_quantize(payload.initial_balance),
    )
    session.add(supplier)
    await session.commit()
    return supplier


async def get_supplier(session: AsyncSession, company_id: uuid.UUID, supplier_id: uuid.UUID) -> Supplier:
    supplier = await supplier_repository.get_by_company_and_id(session, company_id, supplier_id)
    if supplier is None:
        raise NotFoundError("Fournisseur introuvable.")
    return supplier


async def list_suppliers(session: AsyncSession, company_id: uuid.UUID) -> list[Supplier]:
    return await supplier_repository.list_by_company(session, company_id)


async def get_movements(
    session: AsyncSession, company_id: uuid.UUID, supplier_id: uuid.UUID
) -> list[SupplierBalanceMovement]:
    await get_supplier(session, company_id, supplier_id)
    return await supplier_repository.list_movements(session, supplier_id)


async def rebalance_supplier(
    session: AsyncSession,
    company_id: uuid.UUID,
    created_by_id: uuid.UUID,
    supplier_id: uuid.UUID,
    payload: SupplierRebalanceRequest,
) -> SupplierBalanceMovement:
    supplier = await get_supplier(session, company_id, supplier_id)

    wallet = await wallet_repository.lock_by_id(session, payload.wallet_id)
    if wallet is None or wallet.company_id != company_id:
        raise NotFoundError(f"Wallet introuvable : {payload.wallet_id}.")
    if wallet.currency != supplier.currency:
        raise ConflictError(
            f"La devise du wallet ({wallet.currency}) ne correspond pas à celle du fournisseur "
            f"({supplier.currency})."
        )

    amount = _quantize(payload.amount)
    reference = await _generate_unique_reference(session)
    balance_before = supplier.balance

    if payload.type == SupplierMovementType.DEBT:
        direction = MovementDirection.IN
        supplier.balance = _quantize(supplier.balance - amount)
    else:
        direction = MovementDirection.OUT
        supplier.balance = _quantize(supplier.balance + amount)

    await wallet_service.apply_movement(
        session,
        wallet,
        direction,
        amount,
        source_type="supplier_rebalance",
        source_id=supplier.id,
        created_by_id=created_by_id,
        note=payload.note,
    )

    movement = SupplierBalanceMovement(
        supplier_id=supplier.id,
        reference=reference,
        wallet_id=wallet.id,
        type=payload.type,
        amount=amount,
        balance_before=balance_before,
        balance_after=supplier.balance,
        proof_id=payload.proof_id,
        created_by_id=created_by_id,
        note=payload.note,
    )
    session.add(movement)

    await session.commit()
    return movement
