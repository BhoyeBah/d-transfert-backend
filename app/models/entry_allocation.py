import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class EntryAllocationTargetType(StrEnum):
    TRANSFER = "transfer"
    PAYMENT = "payment"


class EntryAllocation(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "entry_allocations"

    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_type: Mapped[EntryAllocationTargetType] = mapped_column(
        Enum(EntryAllocationTargetType, native_enum=False, length=16), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    amount_allocated: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
