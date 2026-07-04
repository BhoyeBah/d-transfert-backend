import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID | None
    user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    note: str | None
    created_at: datetime
