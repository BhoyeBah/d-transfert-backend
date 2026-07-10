import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class SendMode(StrEnum):
    CASH = "cash"
    WAVE = "wave"
    ORANGE_MONEY = "orange_money"
    BANK = "bank"
    OTHER = "other"


class TransferStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Transfer(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "transfers"
    __table_args__ = (UniqueConstraint("company_id", "reference", name="uq_transfers_company_reference"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collaboration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("collaborations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entries.id", ondelete="RESTRICT"), nullable=True
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=True
    )
    client_debt_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    reference: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    beneficiary_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    beneficiary_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    send_mode: Mapped[SendMode] = mapped_column(Enum(SendMode, native_enum=False, length=16), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    private_rate_used: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    collaborative_rate_used: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    converted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, native_enum=False, length=16), default=TransferStatus.PENDING, nullable=False
    )
    proof_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    wallet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class TransferStatusHistory(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "transfer_status_history"

    transfer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transfers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_status: Mapped[TransferStatus | None] = mapped_column(
        Enum(TransferStatus, native_enum=False, length=16), nullable=True
    )
    new_status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, native_enum=False, length=16), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
