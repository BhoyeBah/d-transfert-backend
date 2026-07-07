import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class NationalOperationType(StrEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    EXCHANGE = "exchange"
    REBALANCE = "rebalance"
    ADJUSTMENT = "adjustment"


class NationalOperationStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    CANCELLED = "cancelled"
    CORRECTED = "corrected"


class NationalOperation(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "national_operations"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    type: Mapped[NationalOperationType] = mapped_column(
        Enum(NationalOperationType, native_enum=False, length=16), nullable=False
    )
    status: Mapped[NationalOperationStatus] = mapped_column(
        Enum(NationalOperationStatus, native_enum=False, length=16),
        default=NationalOperationStatus.DRAFT,
        nullable=False,
    )
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    proof_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("national_operations.id", ondelete="SET NULL"), nullable=True
    )
