import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.proof import ProofStatus


class ProofResponse(BaseModel):
    id: uuid.UUID
    transfer_id: uuid.UUID | None
    payment_id: uuid.UUID | None
    company_id: uuid.UUID
    uploaded_by_id: uuid.UUID
    file_name: str
    content_type: str
    file_size: int
    note: str | None
    status: ProofStatus
    created_at: datetime
