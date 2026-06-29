from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from helpmeet_licenses.database import get_db
from helpmeet_licenses.models import License, Activation, LicenseEvent
from helpmeet_licenses.schemas import (
    ActivateRequest, ActivateResponse,
    ValidateRequest, ValidateResponse,
    DeactivateRequest, OkResponse,
)
from helpmeet_licenses.auth import hash_key, create_activation_token, verify_activation_token

router = APIRouter(prefix="/api/license")

def _log_event(db: Session, license_id: int, event_type: str, metadata: dict = None):
    db.add(LicenseEvent(license_id=license_id, event_type=event_type, event_metadata=metadata or {}))

@router.post("/activate", response_model=ActivateResponse)
def activate(req: ActivateRequest, db: Session = Depends(get_db)):
    lic = db.query(License).filter(License.key_hash == hash_key(req.license_key)).first()
    if not lic:
        return ActivateResponse(ok=False, error="license_not_found")
    if lic.status != "active":
        return ActivateResponse(ok=False, error="license_revoked")

    device_hash = hash_key(req.device_id)
    activation = db.query(Activation).filter(
        Activation.license_id == lic.id,
        Activation.device_id_hash == device_hash,
    ).first()
    now = datetime.now(tz=timezone.utc)
    if activation:
        activation.last_seen_at = now
        activation.status = "active"
        if req.app_version:
            activation.app_version = req.app_version
    else:
        activation = Activation(
            license_id=lic.id,
            device_id_hash=device_hash,
            device_name=req.device_name,
            os=req.os,
            app_version=req.app_version,
        )
        db.add(activation)

    _log_event(db, lic.id, "activated", {"device_id_hash": device_hash})
    db.commit()

    token = create_activation_token(
        license_id=lic.id,
        device_id=req.device_id,
        plan=lic.plan,
        updates_until=lic.updates_until,
    )
    return ActivateResponse(
        ok=True,
        activation_token=token,
        plan=lic.plan,
        updates_until=lic.updates_until,
    )

@router.post("/validate", response_model=ValidateResponse)
def validate(req: ValidateRequest, db: Session = Depends(get_db)):
    try:
        payload = verify_activation_token(req.activation_token)
    except ValueError:
        return ValidateResponse(ok=False, error="invalid_token")

    lic = db.get(License, payload["license_id"])
    if not lic or lic.status != "active":
        return ValidateResponse(ok=False, error="license_revoked")

    device_hash = hash_key(req.device_id)
    activation = db.query(Activation).filter(
        Activation.license_id == lic.id,
        Activation.device_id_hash == device_hash,
        Activation.status == "active",
    ).first()
    if activation:
        activation.last_seen_at = datetime.now(tz=timezone.utc)
        if req.app_version:
            activation.app_version = req.app_version
    _log_event(db, lic.id, "validated", {"device_id_hash": device_hash})
    db.commit()
    return ValidateResponse(ok=True, status="active", plan=lic.plan)

@router.post("/deactivate", response_model=OkResponse)
def deactivate(req: DeactivateRequest, db: Session = Depends(get_db)):
    try:
        payload = verify_activation_token(req.activation_token)
    except ValueError:
        return OkResponse(ok=False, error="invalid_token")

    device_hash = hash_key(req.device_id)
    activation = db.query(Activation).filter(
        Activation.license_id == payload["license_id"],
        Activation.device_id_hash == device_hash,
        Activation.status == "active",
    ).first()
    if activation:
        activation.status = "deactivated"
        activation.deactivated_at = datetime.now(tz=timezone.utc)
        _log_event(db, payload["license_id"], "deactivated", {"device_id_hash": device_hash})
        db.commit()
    return OkResponse(ok=True)
