from __future__ import annotations

import asyncio
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from itertools import cycle

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.permission_codes import PERMISSION_DESCRIPTIONS, PermissionCode, RoleCode
from app.core.security import hash_password
from app.models.company import Company, CompanyStatus
from app.models.national_operation import NationalOperationType
from app.models.role import Permission, Role
from app.models.supplier_balance_movement import SupplierMovementType
from app.models.user import User
from app.models.wallet import WalletType
from app.repositories import company_repository, role_repository, user_repository
from app.schemas.collaboration import CollaborationRequestCreate
from app.schemas.employee import EmployeeCreateRequest
from app.schemas.entry import EntryCreateRequest, EntryLineRequest
from app.schemas.national_operation import NationalOperationCreateRequest, NationalOperationLineRequest
from app.schemas.payment import PaymentCreateRequest
from app.schemas.supplier import SupplierCreateRequest, SupplierRebalanceRequest
from app.schemas.transfer import SendMode, TransferCreateRequest
from app.schemas.wallet import WalletCreateRequest
from app.services import (
    collaboration_service,
    employee_service,
    entry_service,
    national_operation_service,
    payment_service,
    proof_service,
    supplier_service,
    transfer_service,
    wallet_service,
)


@dataclass(slots=True)
class SeedAccount:
    company: Company
    owner: User


def _tag() -> str:
    return datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")


async def _ensure_reference_data(session) -> None:
    existing_permission_codes = set((await session.scalars(select(Permission.code))).all())
    for code, description in PERMISSION_DESCRIPTIONS.items():
        if code.value not in existing_permission_codes:
            session.add(Permission(code=code.value, description=description))

    existing_role_codes = set((await session.scalars(select(Role.code))).all())
    for code, name in [
        (RoleCode.OWNER, "Owner"),
        (RoleCode.EMPLOYEE, "Employe"),
        (RoleCode.SUPER_ADMIN, "Super Admin"),
    ]:
        if code.value not in existing_role_codes:
            session.add(Role(code=code.value, name=name, is_system=True))

    await session.flush()


async def _create_company(
    session,
    *,
    name: str,
    phone: str,
    address: str,
    default_currency: str,
    owner_full_name: str,
    owner_password: str,
    owner_role_id,
    seed_tag: str,
    seed_index: int,
) -> SeedAccount:
    registration_code = f"DT-{seed_tag[-6:]}-{seed_index:04d}"
    if await company_repository.get_by_registration_code(session, registration_code) is not None:
        raise RuntimeError(f"Code entreprise deja utilise: {registration_code}.")

    company = Company(
        name=name,
        registration_code=registration_code,
        address=address,
        phone=phone,
        default_currency=default_currency,
        status=CompanyStatus.ACTIVE,
    )
    session.add(company)
    await session.flush()

    owner = User(
        company_id=company.id,
        role_id=owner_role_id,
        matricule=registration_code,
        full_name=owner_full_name,
        phone=phone,
        password_hash=hash_password(owner_password),
        is_owner=True,
        is_super_admin=False,
        is_active=True,
    )
    session.add(owner)
    await session.flush()
    return SeedAccount(company=company, owner=owner)


async def _seed_companies(session, seed_tag: str) -> tuple[SeedAccount, list[SeedAccount]]:
    owner_role = await role_repository.get_role_by_code(session, RoleCode.OWNER)
    if owner_role is None:
        raise RuntimeError("Role owner introuvable. Lance les migrations de reference.")

    main = await _create_company(
        session,
        name=f"D-Transfert Seed Main {seed_tag[-6:]}",
        phone=f"+221770{seed_tag[-6:]}",
        address="Dakar, Senegal",
        default_currency="XOF",
        owner_full_name="Owner Seed Principal",
        owner_password="SeedOwner!2026",
        owner_role_id=owner_role.id,
        seed_tag=seed_tag,
        seed_index=1,
    )

    targets: list[SeedAccount] = []
    for idx in range(1, 16):
        account = await _create_company(
            session,
            name=f"Partenaire Seed {idx:02d} {seed_tag[-4:]}",
            phone=f"+22178{seed_tag[-6:]}{idx:02d}",
            address=f"Adresse partenaire {idx:02d}",
            default_currency="XOF",
            owner_full_name=f"Owner Partenaire {idx:02d}",
            owner_password=f"SeedPartner!{idx:02d}2026",
            owner_role_id=owner_role.id,
            seed_tag=seed_tag,
            seed_index=idx + 1,
        )
        targets.append(account)

    await session.commit()
    return main, targets


async def _load_existing_company(session, registration_code: str) -> SeedAccount:
    company = await company_repository.get_by_registration_code(session, registration_code)
    if company is None:
        raise RuntimeError(f"Entreprise introuvable avec le matricule {registration_code}.")
    owner_user = await user_repository.get_owner_by_company(session, company.id)
    if owner_user is None:
        raise RuntimeError(f"Aucun owner trouve pour l'entreprise {registration_code}.")
    return SeedAccount(company=company, owner=owner_user)


async def _seed_employees(session, company_id, acted_by_user_id: str, seed_tag: str) -> int:
    permission_templates = [
        [
            PermissionCode.DASHBOARD_VIEW,
            PermissionCode.ENTRY_MANAGE,
            PermissionCode.TRANSFER_CREATE,
            PermissionCode.PAYMENT_CREATE,
            PermissionCode.CLIENT_MANAGE,
        ],
        [
            PermissionCode.WALLET_MANAGE,
            PermissionCode.NATIONAL_OPERATION_MANAGE,
            PermissionCode.SUPPLIER_MANAGE,
            PermissionCode.REPORT_VIEW,
            PermissionCode.REPORT_EXPORT,
        ],
        [
            PermissionCode.COLLABORATION_MANAGE,
            PermissionCode.RATE_PRIVATE_VIEW,
            PermissionCode.RATE_PRIVATE_MANAGE,
            PermissionCode.OPERATION_VALIDATE,
            PermissionCode.EMPLOYEE_MANAGE,
        ],
    ]

    created = 0
    for idx in range(1, 16):
        permissions = permission_templates[(idx - 1) % len(permission_templates)]
        payload = EmployeeCreateRequest(
            full_name=f"Employe Seed {idx:02d}",
            phone=f"+22179{seed_tag[-6:]}{idx:02d}",
            password=f"SeedEmployee!{idx:02d}2026",
            permissions=permissions,
        )
        await employee_service.create_employee(session, company_id, acted_by_user_id, payload)
        created += 1
    return created


async def _seed_wallets(session, company_id, created_by_id) -> dict[str, list]:
    wallet_specs = [
        ("Caisse XOF Principale", "XOF", WalletType.CASH, Decimal("50000000")),
        ("Caisse GNF Principale", "GNF", WalletType.CASH, Decimal("50000000")),
        ("Banque XOF", "XOF", WalletType.BANK, Decimal("25000000")),
        ("Banque GNF", "GNF", WalletType.BANK, Decimal("25000000")),
        ("Mobile USD", "USD", WalletType.MOBILE_MONEY, Decimal("25000")),
        ("Mobile EUR", "EUR", WalletType.MOBILE_MONEY, Decimal("25000")),
        ("Transit XOF", "XOF", WalletType.OTHER, Decimal("12000000")),
        ("Transit GNF", "GNF", WalletType.OTHER, Decimal("12000000")),
        ("Caisse USD", "USD", WalletType.CASH, Decimal("40000")),
        ("Caisse EUR", "EUR", WalletType.CASH, Decimal("40000")),
        ("Tresorerie XOF", "XOF", WalletType.OTHER, Decimal("15000000")),
        ("Tresorerie GNF", "GNF", WalletType.OTHER, Decimal("15000000")),
        ("Reserve USD", "USD", WalletType.BANK, Decimal("50000")),
        ("Reserve EUR", "EUR", WalletType.BANK, Decimal("50000")),
        ("Depot XOF", "XOF", WalletType.CASH, Decimal("8000000")),
    ]

    wallets_by_currency: dict[str, list] = {"XOF": [], "GNF": [], "USD": [], "EUR": []}
    for idx, (name, currency, wallet_type, initial_balance) in enumerate(wallet_specs, start=1):
        wallet = await wallet_service.create_wallet(
            session,
            company_id,
            created_by_id,
            WalletCreateRequest(
                name=name,
                code=f"W{idx:02d}{currency}{created_by_id.hex[:4]}",
                type=wallet_type,
                phone=None,
                currency=currency,
                initial_balance=initial_balance,
                description=f"Seed wallet {idx:02d}",
            ),
        )
        wallets_by_currency[currency].append(wallet)

    return wallets_by_currency


async def _seed_suppliers(session, company_id, created_by_id, gnf_wallet) -> int:
    created = 0
    for idx in range(1, 16):
        supplier = await supplier_service.create_supplier(
            session,
            company_id,
            SupplierCreateRequest(
                name=f"Fournisseur Seed {idx:02d}",
                code=f"SUP{idx:02d}{created_by_id.hex[:4]}",
                phone=f"+22177{idx:02d}880{idx:02d}",
                address=f"Adresse fournisseur {idx:02d}",
                currency="GNF",
                initial_balance=Decimal("0"),
                note=f"Seed fournisseur {idx:02d}",
            ),
        )
        movement_type = SupplierMovementType.DEBT if idx % 2 else SupplierMovementType.PAYMENT
        await supplier_service.rebalance_supplier(
            session,
            company_id,
            created_by_id,
            supplier.id,
            SupplierRebalanceRequest(
                type=movement_type,
                amount=Decimal("25000") + Decimal(idx) * Decimal("1000"),
                wallet_id=gnf_wallet.id,
                proof_id=None,
                note=f"Seed rebalance {idx:02d}",
            ),
        )
        created += 1
    return created


async def _seed_collaborations_and_operations(
    session,
    main: SeedAccount,
    targets: list[SeedAccount],
    xof_wallets: list,
    gnf_wallets: list,
    seed_tag: str,
) -> dict[str, int]:
    if len(xof_wallets) < 2 or len(gnf_wallets) < 2:
        raise RuntimeError("Il faut au moins 2 wallets XOF et 2 wallets GNF pour les entrées et operations.")

    xof_entry_wallet = xof_wallets[0]
    gnf_entry_wallet = gnf_wallets[0]
    xof_operation_in_wallet = xof_wallets[1]
    xof_operation_out_wallet = xof_wallets[-1]

    send_modes = cycle(list(SendMode))
    national_types = cycle(list(NationalOperationType))

    collaboration_count = 0
    entry_count = 0
    transfer_count = 0
    payment_count = 0
    proof_count = 0
    national_operation_count = 0

    for idx, target in enumerate(targets, start=1):
        rate = Decimal("1.050000") + (Decimal(idx) / Decimal("100"))
        collaboration, _proposal = await collaboration_service.request_collaboration(
            session,
            main.company.id,
            CollaborationRequestCreate(
                target_matricule=target.company.registration_code,
                currency="XOF",
                initial_rate=rate,
                note=f"Seed collaboration {idx:02d}",
            ),
        )
        await collaboration_service.accept_collaboration(
            session,
            target.company.id,
            target.owner.id,
            collaboration.id,
        )
        collaboration_count += 1

        xof_amount = Decimal("400000") + Decimal(idx) * Decimal("10000")
        gnf_amount = Decimal("300000") + Decimal(idx) * Decimal("7500")
        client_name = f"Client Seed {idx:02d}"
        client_phone = f"+22176{idx:02d}{seed_tag[-6:]}"

        entry, _ = await entry_service.create_entry(
            session,
            main.company.id,
            main.owner.id,
            EntryCreateRequest(
                client_name=client_name,
                client_phone=client_phone,
                note=f"Seed entry {idx:02d}",
                lines=[
                    EntryLineRequest(
                        wallet_id=xof_entry_wallet.id,
                        amount=xof_amount,
                        currency="XOF",
                        note=f"Ligne XOF {idx:02d}",
                    ),
                    EntryLineRequest(
                        wallet_id=gnf_entry_wallet.id,
                        amount=gnf_amount,
                        currency="GNF",
                        note=f"Ligne GNF {idx:02d}",
                    ),
                ],
            ),
        )
        entry_count += 1

        transfer = await transfer_service.create_transfer(
            session,
            main.company.id,
            main.owner.id,
            TransferCreateRequest(
                collaboration_id=collaboration.id,
                entry_id=entry.id,
                amount=xof_amount + Decimal("30000"),
                currency="XOF",
                beneficiary_name=f"Beneficiaire {idx:02d}",
                beneficiary_phone=f"+22175{idx:02d}{seed_tag[-6:]}",
                send_mode=next(send_modes),
                note=f"Seed transfer {idx:02d}",
                reliquat_action="unallocated",
            ),
        )
        await transfer_service.approve_transfer(
            session,
            target.company.id,
            target.owner.id,
            transfer.id,
            proof_id=None,
        )
        await proof_service.upload_transfer_proof(
            session,
            main.company.id,
            main.owner.id,
            transfer.id,
            file_name=f"transfer-seed-{idx:02d}.png",
            content_type="image/png",
            content=b"\x89PNG\r\n\x1a\nseed-transfer-proof",
            note=f"Preuve seed transfer {idx:02d}",
        )
        transfer_count += 1
        proof_count += 1

        payment = await payment_service.create_payment(
            session,
            main.company.id,
            main.owner.id,
            PaymentCreateRequest(
                collaboration_id=collaboration.id,
                wallet_id=gnf_entry_wallet.id,
                amount=gnf_amount + Decimal("30000"),
                currency="GNF",
                client_name=client_name,
                client_phone=client_phone,
                note=f"Seed payment {idx:02d}",
                reliquat_action="unallocated",
            ),
        )
        await payment_service.approve_payment(
            session,
            target.company.id,
            target.owner.id,
            payment.id,
            proof_id=None,
        )
        payment_count += 1

        operation_amount = Decimal("25000") + Decimal(idx) * Decimal("2500")
        operation_type = next(national_types)
        await national_operation_service.create_operation(
            session,
            main.company.id,
            operation_type,
            main.owner.id,
            NationalOperationCreateRequest(
                client_name=f"Operation Client {idx:02d}",
                client_phone=f"+22174{idx:02d}{seed_tag[-6:]}",
                note=f"Seed operation nationale {idx:02d}",
                exchange_rate=None,
                lines=[
                    NationalOperationLineRequest(
                        wallet_id=xof_operation_in_wallet.id,
                        amount_in=operation_amount,
                        amount_out=Decimal("0"),
                        currency="XOF",
                        note=f"Entree XOF {idx:02d}",
                    ),
                    NationalOperationLineRequest(
                        wallet_id=xof_operation_out_wallet.id,
                        amount_in=Decimal("0"),
                        amount_out=operation_amount,
                        currency="XOF",
                        note=f"Sortie XOF {idx:02d}",
                    ),
                ],
            ),
        )
        national_operation_count += 1

    return {
        "collaborations": collaboration_count,
        "entries": entry_count,
        "transfers": transfer_count,
        "payments": payment_count,
        "proofs": proof_count,
        "national_operations": national_operation_count,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed de donnees fictives pour D-Transfert.")
    parser.add_argument(
        "--company-code",
        default=None,
        help="Matricule de l'entreprise existante a peupler. Si absent, cree un tenant de demo.",
    )
    args = parser.parse_args()

    seed_tag = _tag()
    async with AsyncSessionLocal() as session:
        await _ensure_reference_data(session)

        if args.company_code:
            main_account = await _load_existing_company(session, args.company_code)
            target_accounts: list[SeedAccount] = []
            owner_role = await role_repository.get_role_by_code(session, RoleCode.OWNER)
            if owner_role is None:
                raise RuntimeError("Role owner introuvable. Lance les migrations de reference.")
            for idx in range(1, 16):
                target_accounts.append(
                    await _create_company(
                        session,
                        name=f"Partenaire Seed {idx:02d} {seed_tag[-4:]}",
                        phone=f"+22178{seed_tag[-6:]}{idx:02d}",
                        address=f"Adresse partenaire {idx:02d}",
                        default_currency="XOF",
                        owner_full_name=f"Owner Partenaire {idx:02d}",
                        owner_password=f"SeedPartner!{idx:02d}2026",
                        owner_role_id=owner_role.id,
                        seed_tag=seed_tag,
                        seed_index=idx,
                    )
                )
            await session.commit()
        else:
            main_account, target_accounts = await _seed_companies(session, seed_tag)

        employees = await _seed_employees(session, main_account.company.id, main_account.owner.id, seed_tag)
        wallets_by_currency = await _seed_wallets(session, main_account.company.id, main_account.owner.id)
        suppliers = await _seed_suppliers(
            session,
            main_account.company.id,
            main_account.owner.id,
            wallets_by_currency["GNF"][0],
        )
        commerce = await _seed_collaborations_and_operations(
            session,
            main_account,
            target_accounts,
            wallets_by_currency["XOF"],
            wallets_by_currency["GNF"],
            seed_tag,
        )

        print("Seed termine.")
        print(f"- Entreprises creees: {1 + len(target_accounts)}")
        print(f"- Employes creees: {employees}")
        print(f"- Wallets creees: {sum(len(items) for items in wallets_by_currency.values())}")
        print(f"- Fournisseurs creees: {suppliers}")
        print(f"- Collaborations creees: {commerce['collaborations']}")
        print(f"- Entrees creees: {commerce['entries']}")
        print(f"- Transferts creees: {commerce['transfers']}")
        print(f"- Paiements crees: {commerce['payments']}")
        print(f"- Preuves creees: {commerce['proofs']}")
        print(f"- Operations nationales creees: {commerce['national_operations']}")
        print("Notifications et audit logs ont ete generes automatiquement par les services.")


if __name__ == "__main__":
    asyncio.run(main())
