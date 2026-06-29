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

import hmac
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session

from helpmeet_licenses.auth import hash_key
from helpmeet_licenses.config import settings
from helpmeet_licenses.database import get_db
from helpmeet_licenses.keys import generate_license_key
from helpmeet_licenses.models import Customer, License, LicenseEvent
from helpmeet_licenses.schemas import OkResponse

router = APIRouter(prefix="/api/gumroad", tags=["gumroad"])

PLAN_MAP = {
    "helpmeet_personal": "personal",
    "helpmeet_pro": "pro",
    "helpmeet_team": "team",
}


def _require_token(token: str = Query(..., alias="token")):
    if not hmac.compare_digest(token, settings.admin_api_key):
        raise HTTPException(status_code=403, detail="Forbidden")


def _find_purchase_event(db: Session, sale_id: str):
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
async def gumroad_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(_require_token),
):
    # Gumroad envía form-urlencoded; también aceptamos JSON para pruebas
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        import json as _json
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    email = data.get("email", "")
    sale_id = data.get("sale_id", "") or data.get("order_number", "")
    product_id = data.get("product_id") or data.get("permalink") or "helpmeet_personal"
    refunded = str(data.get("refunded", "false")).lower() in ("true", "1")
    dispute = str(data.get("disputed", data.get("dispute", "false"))).lower() in ("true", "1")

    if not email or not sale_id:
        return OkResponse(ok=False, error="missing_fields")

    existing_event = _find_purchase_event(db, sale_id)

    if refunded or dispute:
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
                        event_metadata={"sale_id": sale_id, "reason": "gumroad_refund"},
                    )
                )
                db.commit()
        return OkResponse(ok=True)

    if existing_event:
        return OkResponse(ok=True)

    # New purchase: find or create customer
    customer = db.query(Customer).filter(Customer.email == email).first()
    if not customer:
        customer = Customer(email=email)
        db.add(customer)
        db.flush()

    # Determine plan
    plan = PLAN_MAP.get(product_id, "personal")

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
            event_metadata={"sale_id": sale_id, "product_id": product_id, "email": email},
        )
    )
    db.commit()

    return OkResponse(ok=True)
