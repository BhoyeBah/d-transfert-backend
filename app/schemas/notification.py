import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: NotificationType
    message: str
    link_type: str | None
    link_id: uuid.UUID | None
    is_read: bool
    created_at: datetime
