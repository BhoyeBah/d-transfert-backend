import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class CollaborationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class RateProposalStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Collaboration(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "collaborations"

    initiator_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[CollaborationStatus] = mapped_column(
        Enum(CollaborationStatus, native_enum=False, length=16),
        default=CollaborationStatus.PENDING,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Pas de contrainte FK DB (référence circulaire avec collaboration_rate_history) :
    # pointeur applicatif maintenu uniquement par CollaborationService.
    current_rate_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class CollaborationRateHistory(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "collaboration_rate_history"

    collaboration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("collaborations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    new_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    status: Mapped[RateProposalStatus] = mapped_column(
        Enum(RateProposalStatus, native_enum=False, length=16),
        default=RateProposalStatus.PROPOSED,
        nullable=False,
    )
    proposed_by_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    decided_by_company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
