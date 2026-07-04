import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import ConflictError, InsufficientBalanceError
from app.core.security import hash_password
from app.models.company import Company, CompanyStatus
from app.models.user import User
from app.models.wallet import Wallet, WalletStatus, WalletType
from app.models.wallet_movement import MovementDirection
from app.services import wallet_service


async def _seed_company_and_user(db_session):
    company = Company(
        name="Entreprise Test",
        registration_code=f"DT-{uuid.uuid4().hex[:8].upper()}",
        phone=f"+2246{uuid.uuid4().int % 100000000:08d}",
        default_currency="GNF",
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    await db_session.flush()

    user = User(
        company_id=company.id,
        matricule=company.registration_code,
        full_name="Owner Test",
        phone=company.phone,
        password_hash=hash_password("Secret123!"),
        is_owner=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return company, user


async def test_apply_movement_rejects_insufficient_balance(db_session):
    company, user = await _seed_company_and_user(db_session)
    wallet = Wallet(
        company_id=company.id,
        name="Caisse Cash",
        code="CASH",
        type=WalletType.CASH,
        currency="GNF",
        balance=Decimal("5000"),
        status=WalletStatus.ACTIVE,
    )
    db_session.add(wallet)
    await db_session.flush()

    with pytest.raises(InsufficientBalanceError) as exc_info:
        await wallet_service.apply_movement(
            db_session,
            wallet,
            MovementDirection.OUT,
            Decimal("10000"),
            source_type="test",
            source_id=uuid.uuid4(),
            created_by_id=user.id,
        )

    assert "Solde insuffisant dans le wallet Caisse Cash" in str(exc_info.value)
    assert wallet.balance == Decimal("5000")


async def test_apply_movement_rejects_inactive_wallet(db_session):
    company, user = await _seed_company_and_user(db_session)
    wallet = Wallet(
        company_id=company.id,
        name="Caisse Inactive",
        code="CASH2",
        type=WalletType.CASH,
        currency="GNF",
        balance=Decimal("5000"),
        status=WalletStatus.INACTIVE,
    )
    db_session.add(wallet)
    await db_session.flush()

    with pytest.raises(ConflictError):
        await wallet_service.apply_movement(
            db_session,
            wallet,
            MovementDirection.IN,
            Decimal("1000"),
            source_type="test",
            source_id=uuid.uuid4(),
            created_by_id=user.id,
        )


async def test_apply_movement_updates_balance_and_records_movement(db_session):
    company, user = await _seed_company_and_user(db_session)
    wallet = Wallet(
        company_id=company.id,
        name="Caisse Cash",
        code="CASH3",
        type=WalletType.CASH,
        currency="GNF",
        balance=Decimal("5000"),
        status=WalletStatus.ACTIVE,
    )
    db_session.add(wallet)
    await db_session.flush()

    movement = await wallet_service.apply_movement(
        db_session,
        wallet,
        MovementDirection.OUT,
        Decimal("2000"),
        source_type="test",
        source_id=uuid.uuid4(),
        created_by_id=user.id,
    )

    assert wallet.balance == Decimal("3000")
    assert movement.balance_before == Decimal("5000")
    assert movement.balance_after == Decimal("3000")
