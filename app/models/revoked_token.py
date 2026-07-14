from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class RevokedToken(Base, UUIDPKMixin, TimestampMixin):
    """Jetons explicitement révoqués (déconnexion) avant leur expiration naturelle.

    `expires_at` recopie l'expiration du JWT lui-même : passé ce délai, la ligne n'a
    plus d'utilité (le token serait de toute façon rejeté par sa propre expiration) et
    peut être purgée.
    """

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
