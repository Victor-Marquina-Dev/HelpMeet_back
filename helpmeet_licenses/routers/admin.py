import hmac
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from helpmeet_licenses.config import settings
from helpmeet_licenses.database import get_db
from helpmeet_licenses.keys import generate_license_key
from helpmeet_licenses.models import Customer, License, Activation, LicenseEvent
from helpmeet_licenses.schemas import (
    CreateCustomerRequest, CustomerOut,
    CreateLicenseRequest, CreateLicenseResponse, LicenseOut, OkResponse,
)
from helpmeet_licenses.auth import hash_key

router = APIRouter(prefix="/api/admin")

# Error messages
LICENSE_NOT_FOUND = "License not found"

def _require_admin(x_admin_key: str = Header(...)):
    if not hmac.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(status_code=403, detail="Forbidden")

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
    key = generate_license_key()
    lic = License(
        customer_id=req.customer_id,
        key_hash=hash_key(key),
        key_last4=key[-4:],
        plan=req.plan,
        updates_until=req.updates_until,
        max_devices=req.max_devices,
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
        raise HTTPException(status_code=404, detail=LICENSE_NOT_FOUND)
    return lic

@router.post("/licenses/{license_id}/revoke", response_model=OkResponse)
def revoke_license(license_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(status_code=404, detail=LICENSE_NOT_FOUND)
    lic.status = "revoked"
    lic.revoked_at = datetime.now(tz=timezone.utc)
    _log_event(db, lic.id, "revoked")
    db.commit()
    return OkResponse(ok=True)


@router.post("/licenses/{license_id}/reset-devices", response_model=OkResponse)
def reset_devices(license_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(status_code=404, detail=LICENSE_NOT_FOUND)
    db.query(Activation).filter(
        Activation.license_id == license_id,
        Activation.status == "active"
    ).update({"status": "deactivated"})
    _log_event(db, license_id, "devices_reset")
    db.commit()
    return OkResponse(ok=True)


ADMIN_NOTIFY_EMAIL = "victormarquina591@gmail.com"


def _notify_key_via_resend(customer_email: str, key: str, plan: str, license_id: int) -> None:
    """Notifica a Victor via Resend (HTTPS) con los datos para reenviar al cliente."""
    if not settings.resend_api_key:
        return
    try:
        import resend
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": "Helpmeet Admin <onboarding@resend.dev>",
            "to": ADMIN_NOTIFY_EMAIL,
            "subject": f"Clave lista para enviar — {customer_email}",
            "html": f"""
<div style="font-family:sans-serif;max-width:500px;margin:0 auto;padding:32px;background:#0f1110;color:#e3e2e0">
  <h2 style="color:#aacfbf;margin-bottom:4px">Clave lista para enviar</h2>
  <p style="color:#8b928e;margin-bottom:20px">Reenvia este email al cliente o copia la clave manualmente.</p>

  <div style="background:#1a1c1b;border-radius:10px;padding:16px;margin-bottom:16px">
    <div style="font-size:11px;color:#8b928e">ENVIAR A</div>
    <div style="font-size:16px;margin-top:4px;color:#e3e2e0">{customer_email}</div>
  </div>

  <div style="background:#1a1c1b;border-radius:10px;padding:20px;margin-bottom:16px;text-align:center">
    <div style="font-size:11px;color:#8b928e;margin-bottom:10px">PRODUCT KEY</div>
    <code style="font-size:22px;letter-spacing:3px;color:#aacfbf;font-weight:bold">{key}</code>
  </div>

  <div style="background:#1a1c1b;border-radius:8px;padding:14px;font-size:13px;color:#8b928e">
    Plan: {plan} &nbsp;|&nbsp; Licencia #{license_id}
  </div>

  <hr style="border:none;border-top:1px solid #2a2c2b;margin:20px 0">
  <p style="font-size:12px;color:#8b928e">
    <strong style="color:#aacfbf">Texto para reenviar al cliente:</strong><br><br>
    Hola, tu Product Key de Helpmeet es:<br>
    <code style="color:#aacfbf">{key}</code><br><br>
    Abre Helpmeet e introducela cuando se solicite.<br>
    Soporte: victor.marquina30@gmail.com
  </p>
</div>"""
        })
    except Exception:
        pass


@router.post("/licenses/{license_id}/generate-key")
def generate_key_for_license(license_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    """Genera nueva key, la envía por Gmail y la devuelve al panel."""
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(status_code=404, detail=LICENSE_NOT_FOUND)
    if not lic.customer or not lic.customer.email:
        raise HTTPException(status_code=400, detail="No customer email")

    new_key = generate_license_key()
    lic.key_hash = hash_key(new_key)
    lic.key_last4 = new_key[-4:]
    _log_event(db, license_id, "key_generated")
    db.commit()

    customer_email = lic.customer.email
    plan_str = lic.plan

    # Notificar via Resend (HTTPS — Railway no bloquea HTTPS, sí bloquea SMTP)
    import threading
    threading.Thread(
        target=_notify_key_via_resend,
        args=(customer_email, new_key, plan_str, license_id),
        daemon=True
    ).start()

    return {
        "ok": True,
        "key": new_key,
        "email": customer_email,
        "plan": plan_str,
        "email_sent": bool(settings.resend_api_key),
        "email_error": None if settings.resend_api_key else "RESEND_API_KEY no configurado",
    }
