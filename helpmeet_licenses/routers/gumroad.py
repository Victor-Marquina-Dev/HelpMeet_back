"""
POST /api/gumroad/webhook

Recibe eventos de Gumroad (compra, reembolso) y crea/actualiza licencias.

Payload esperado de Gumroad (simplificado):
  {
    "email": "buyer@example.com",
    "sale_id": "abc123",
    "product_id": "helpmeet_personal",
    "refunded": false,   # true si es reembolso
    "dispute": false     # true si es disputa
  }

Seguridad: Gumroad no envía signature en el tier básico.
Usamos la misma ADMIN_API_KEY en header X-Admin-Key para validar llamadas locales/simuladas.
En producción, se puede añadir validación de IP de Gumroad como capa extra.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from helpmeet_licenses.auth import hash_key
from helpmeet_licenses.database import get_db
from helpmeet_licenses.keys import generate_license_key
from helpmeet_licenses.models import Customer, License, LicenseEvent
from helpmeet_licenses.routers.admin import _require_admin
from helpmeet_licenses.schemas import OkResponse

router = APIRouter(prefix="/api/gumroad", tags=["gumroad"])

PLAN_MAP = {
    "helpmeet_personal": "personal",
    "helpmeet_pro": "pro",
    "helpmeet_team": "team",
}


class GumroadWebhookPayload(BaseModel):
    email: EmailStr
    sale_id: str
    product_id: str
    refunded: bool = False
    dispute: bool = False


def _find_purchase_event(db: Session, sale_id: str):
    """Find a gumroad_purchase event by sale_id. Uses Python-level filtering
    for SQLite compatibility (avoids PostgreSQL JSON operators)."""
    events = (
        db.query(LicenseEvent)
        .filter(LicenseEvent.event_type == "gumroad_purchase")
        .all()
    )
    return next(
        (e for e in events if e.event_metadata.get("sale_id") == sale_id),
        None,
    )


@router.post("/webhook", response_model=OkResponse)
def gumroad_webhook(
    payload: GumroadWebhookPayload,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    existing_event = _find_purchase_event(db, payload.sale_id)

    if payload.refunded or payload.dispute:
        # Handle refund/dispute: revoke the license
        if existing_event:
            lic = db.get(License, existing_event.license_id)
            if lic and lic.status == "active":
                lic.status = "refunded"
                lic.revoked_at = datetime.now(tz=timezone.utc)
                db.add(
                    LicenseEvent(
                        license_id=lic.id,
                        event_type="refunded",
                        event_metadata={
                            "sale_id": payload.sale_id,
                            "reason": "gumroad_refund",
                        },
                    )
                )
                db.commit()
        return OkResponse(ok=True)

    if existing_event:
        # Already processed this purchase — idempotent
        return OkResponse(ok=True)

    # New purchase: find or create customer
    customer = db.query(Customer).filter(Customer.email == payload.email).first()
    if not customer:
        customer = Customer(email=payload.email)
        db.add(customer)
        db.flush()

    # Determine plan
    plan = PLAN_MAP.get(payload.product_id, "personal")

    # Create license
    key = generate_license_key()
    lic = License(
        customer_id=customer.id,
        key_hash=hash_key(key),
        key_last4=key[-4:],
        plan=plan,
        max_devices=1,
    )
    db.add(lic)
    db.flush()

    # Log purchase event (stores sale_id for idempotency)
    db.add(
        LicenseEvent(
            license_id=lic.id,
            event_type="gumroad_purchase",
            event_metadata={
                "sale_id": payload.sale_id,
                "product_id": payload.product_id,
                "email": payload.email,
            },
        )
    )
    db.commit()

    return OkResponse(ok=True)
