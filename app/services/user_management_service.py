import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client_balance_movement import ClientBalanceMovement
from app.models.entry import Entry
from app.models.national_operation import NationalOperation
from app.models.payment import Payment
from app.models.password_reset_otp import PasswordResetOTP
from app.models.private_sending_rate import PrivateSendingRate
from app.models.proof import Proof
from app.models.role import UserPermissionOverride
from app.models.system_log import SystemLog
from app.models.supplier_balance_movement import SupplierBalanceMovement
from app.models.transfer import Transfer
from app.models.wallet_movement import WalletMovement


async def count_user_dependency_usage(session: AsyncSession, user_id: uuid.UUID) -> dict[str, int]:
    """Compte les références qui empêchent la suppression physique d'un utilisateur."""

    queries = {
        "entries": select(func.count()).select_from(Entry).where(Entry.created_by_id == user_id),
        "transfers": select(func.count()).select_from(Transfer).where(Transfer.created_by_id == user_id),
        "payments": select(func.count()).select_from(Payment).where(Payment.created_by_id == user_id),
        "wallet_movements": select(func.count()).select_from(WalletMovement).where(
            WalletMovement.created_by_id == user_id
        ),
        "national_operations": select(func.count()).select_from(NationalOperation).where(
            NationalOperation.created_by_id == user_id
        ),
        "supplier_balance_movements": select(func.count()).select_from(SupplierBalanceMovement).where(
            SupplierBalanceMovement.created_by_id == user_id
        ),
        "client_balance_movements": select(func.count()).select_from(ClientBalanceMovement).where(
            ClientBalanceMovement.created_by_id == user_id
        ),
        "proofs": select(func.count()).select_from(Proof).where(Proof.uploaded_by_id == user_id),
        "private_sending_rates": select(func.count()).select_from(PrivateSendingRate).where(
            PrivateSendingRate.created_by_id == user_id
        ),
        "user_permission_overrides": select(func.count()).select_from(UserPermissionOverride).where(
            UserPermissionOverride.user_id == user_id
        ),
        "password_reset_otps": select(func.count()).select_from(PasswordResetOTP).where(
            PasswordResetOTP.user_id == user_id
        ),
        "system_logs": select(func.count()).select_from(SystemLog).where(SystemLog.user_id == user_id),
    }

    counts: dict[str, int] = {}
    for key, stmt in queries.items():
        result = await session.execute(stmt)
        counts[key] = int(result.scalar_one())
    return counts


def has_user_dependencies(counts: dict[str, int]) -> bool:
    return any(count > 0 for count in counts.values())
