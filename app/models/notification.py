import uuid
from enum import StrEnum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class NotificationType(StrEnum):
    COLLABORATION_REQUEST = "collaboration_request"
    COLLABORATION_ACCEPTED = "collaboration_accepted"
    COLLABORATION_REJECTED = "collaboration_rejected"
    TRANSFER_PENDING = "transfer_pending"
    TRANSFER_REJECTED = "transfer_rejected"
    TRANSFER_CANCELLED = "transfer_cancelled"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_REJECTED = "payment_rejected"
    PAYMENT_CANCELLED = "payment_cancelled"
    RATE_PROPOSED = "rate_proposed"


class Notification(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "notifications"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False, length=32), nullable=False
    )
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    link_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    link_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
