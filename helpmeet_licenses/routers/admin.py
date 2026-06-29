import hmac
import secrets
import string
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from helpmeet_licenses.config import settings
from helpmeet_licenses.database import get_db
from helpmeet_licenses.models import Customer, License, LicenseEvent
from helpmeet_licenses.schemas import (
    CreateCustomerRequest, CustomerOut,
    CreateLicenseRequest, CreateLicenseResponse, LicenseOut, OkResponse,
)
from helpmeet_licenses.auth import hash_key

router = APIRouter(prefix="/api/admin")

def _require_admin(x_admin_key: str = Header(...)):
    if not hmac.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(status_code=403, detail="Forbidden")

def _generate_key() -> str:
    alphabet = string.ascii_uppercase + string.digits
    def segment(n=4):
        return "".join(secrets.choice(alphabet) for _ in range(n))
    return f"HM-{segment()}-{segment()}-{segment()}-{segment()}"

def _log_event(db: Session, license_id: int, event_type: str):
    db.add(LicenseEvent(license_id=license_id, event_type=event_type, event_metadata={}))

@router.post("/customers", response_model=CustomerOut)
def create_customer(req: CreateCustomerRequest, db: Session = Depends(get_db),
                    _=Depends(_require_admin)):
    customer = Customer(email=req.email, name=req.name)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

@router.get("/customers", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db), _=Depends(_require_admin)):
    return db.query(Customer).all()

@router.post("/licenses", response_model=CreateLicenseResponse)
def create_license(req: CreateLicenseRequest, db: Session = Depends(get_db),
                   _=Depends(_require_admin)):
    key = _generate_key()
    lic = License(
        customer_id=req.customer_id,
        key_hash=hash_key(key),
        key_last4=key[-4:],
        plan=req.plan,
        updates_until=req.updates_until,
    )
    db.add(lic)
    db.flush()
    _log_event(db, lic.id, "created")
    db.commit()
    db.refresh(lic)
    return CreateLicenseResponse(id=lic.id, license_key=key, key_last4=key[-4:], plan=lic.plan)

@router.get("/licenses", response_model=list[LicenseOut])
def list_licenses(plan: Optional[str] = None, status: Optional[str] = None,
                  db: Session = Depends(get_db), _=Depends(_require_admin)):
    q = db.query(License)
    if plan:
        q = q.filter(License.plan == plan)
    if status:
        q = q.filter(License.status == status)
    return q.all()

@router.get("/licenses/{license_id}", response_model=LicenseOut)
def get_license(license_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    return lic

@router.post("/licenses/{license_id}/revoke", response_model=OkResponse)
def revoke_license(license_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    lic.status = "revoked"
    lic.revoked_at = datetime.now(tz=timezone.utc)
    _log_event(db, lic.id, "revoked")
    db.commit()
    return OkResponse(ok=True)
