import uuid

from pydantic import BaseModel, Field

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


class AdminCompanyStatusUpdateRequest(BaseModel):
    status: CompanyStatus


class AdminCompanyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    address: str | None = None
    phone: str | None = Field(default=None, min_length=6, max_length=32)
    default_currency: str | None = Field(default=None, min_length=3, max_length=8)
