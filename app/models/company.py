from enum import StrEnum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class CompanyStatus(StrEnum):
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"


class Company(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    default_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[CompanyStatus] = mapped_column(
        Enum(CompanyStatus, native_enum=False, length=16),
        default=CompanyStatus.ACTIVE,
        nullable=False,
    )
