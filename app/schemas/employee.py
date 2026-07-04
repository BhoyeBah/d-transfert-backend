import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.permission_codes import PermissionCode


class EmployeeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=6, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    permissions: list[PermissionCode] = Field(default_factory=list)


class EmployeePermissionsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grant: list[PermissionCode] = Field(default_factory=list)
    revoke: list[PermissionCode] = Field(default_factory=list)


class EmployeeStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool


class EmployeeResponse(BaseModel):
    id: uuid.UUID
    matricule: str
    full_name: str
    phone: str
    is_active: bool
    permissions: list[PermissionCode]
    created_at: datetime
