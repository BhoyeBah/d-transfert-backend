import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class WalletType(StrEnum):
    CASH = "cash"
    MOBILE_MONEY = "mobile_money"
    BANK = "bank"
    OTHER = "other"


class WalletStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Wallet(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_wallet_company_code"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    type: Mapped[WalletType] = mapped_column(Enum(WalletType, native_enum=False, length=16), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    status: Mapped[WalletStatus] = mapped_column(
        Enum(WalletStatus, native_enum=False, length=16), default=WalletStatus.ACTIVE, nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
