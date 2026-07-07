from decimal import Decimal

from sqlalchemy import Boolean, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class PlatformSetting(Base, UUIDPKMixin, TimestampMixin):
    """Singleton row: a single PlatformSetting always exists, created lazily on first read."""

    __tablename__ = "platform_settings"

    supported_currencies: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    max_transaction_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_company_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
