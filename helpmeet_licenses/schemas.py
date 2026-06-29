from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

# ── Requests ──────────────────────────────────────────────


class ActivateRequest(BaseModel):
    license_key: str = Field(min_length=12, max_length=64)
    device_id: str = Field(min_length=8, max_length=128)
    device_name: Optional[str] = Field(default=None, max_length=255)
    app_version: Optional[str] = Field(default=None, max_length=30)
    os: Optional[str] = Field(default=None, max_length=100)

    @field_validator("license_key", "device_id", "device_name", "app_version", "os")
    @classmethod
    def _strip_text(cls, value: Optional[str]):
        return value.strip() if isinstance(value, str) else value

    @field_validator("license_key")
    @classmethod
    def _normalize_license_key(cls, value: str):
        return value.strip().upper()


class ValidateRequest(BaseModel):
    activation_token: str = Field(min_length=1, max_length=4096)
    device_id: str = Field(min_length=8, max_length=128)
    app_version: Optional[str] = Field(default=None, max_length=30)

    @field_validator("activation_token", "device_id", "app_version")
    @classmethod
    def _strip_text(cls, value: Optional[str]):
        return value.strip() if isinstance(value, str) else value


class DeactivateRequest(BaseModel):
    activation_token: str = Field(min_length=1, max_length=4096)
    device_id: str = Field(min_length=8, max_length=128)

    @field_validator("activation_token", "device_id")
    @classmethod
    def _strip_text(cls, value: str):
        return value.strip()


class CreateCustomerRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(default=None, max_length=255)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: str):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: Optional[str]):
        return value.strip() if isinstance(value, str) else value


class CreateLicenseRequest(BaseModel):
    customer_id: int
    plan: Literal["personal", "pro", "team"] = "personal"
    updates_until: Optional[date] = None
    max_devices: int = Field(default=1, ge=1, le=25)


# ── Responses ─────────────────────────────────────────────


class ActivateResponse(BaseModel):
    ok: bool
    activation_token: Optional[str] = None
    plan: Optional[str] = None
    updates_until: Optional[date] = None
    error: Optional[str] = None


class ValidateResponse(BaseModel):
    ok: bool
    status: Optional[str] = None
    plan: Optional[str] = None
    error: Optional[str] = None


class OkResponse(BaseModel):
    ok: bool
    error: Optional[str] = None


class CustomerOut(BaseModel):
    id: int
    email: str
    name: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivationOut(BaseModel):
    id: int
    device_name: Optional[str]
    os: Optional[str]
    app_version: Optional[str]
    status: str
    first_activated_at: datetime
    last_seen_at: datetime

    model_config = {"from_attributes": True}


class CreateLicenseResponse(BaseModel):
    id: int
    license_key: str
    key_last4: str
    plan: str


class LicenseOut(BaseModel):
    id: int
    key_last4: str
    plan: str
    status: str
    updates_until: Optional[date]
    max_devices: int = 1
    created_at: datetime
    customer: CustomerOut
    activations: list[ActivationOut] = []

    model_config = {"from_attributes": True}
