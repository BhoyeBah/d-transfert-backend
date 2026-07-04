import uuid

from pydantic import BaseModel

from app.models.company import CompanyStatus


class CompanyMeResponse(BaseModel):
    id: uuid.UUID
    name: str
    registration_code: str
    address: str | None
    phone: str
    default_currency: str
    status: CompanyStatus


class CompanyPublicLookupResponse(BaseModel):
    name: str
    registration_code: str
    phone: str
    address: str | None
    status: CompanyStatus
