import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class EntryStatus(StrEnum):
    UNALLOCATED = "unallocated"
    PARTIALLY_ALLOCATED = "partially_allocated"
    ALLOCATED = "allocated"
    CONSUMED = "consumed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Entry(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "entries"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[EntryStatus] = mapped_column(
        Enum(EntryStatus, native_enum=False, length=24), default=EntryStatus.UNALLOCATED, nullable=False
    )
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entries.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
