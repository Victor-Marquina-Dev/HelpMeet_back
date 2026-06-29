from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

# ── Requests ──────────────────────────────────────────────


class ActivateRequest(BaseModel):
    license_key: str
    device_id: str
    device_name: Optional[str] = None
    app_version: Optional[str] = None
    os: Optional[str] = None


class ValidateRequest(BaseModel):
    activation_token: str
    device_id: str
    app_version: Optional[str] = None


class DeactivateRequest(BaseModel):
    activation_token: str
    device_id: str


class CreateCustomerRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class CreateLicenseRequest(BaseModel):
    customer_id: int
    plan: str = "personal"
    updates_until: Optional[date] = None


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


class LicenseOut(BaseModel):
    id: int
    key_last4: str
    plan: str
    status: str
    updates_until: Optional[date]
    created_at: datetime
    customer: CustomerOut
    activations: list[ActivationOut] = []

    model_config = {"from_attributes": True}
