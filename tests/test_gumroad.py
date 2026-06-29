import pytest
from helpmeet_licenses.config import settings
from helpmeet_licenses.models import Customer, License, LicenseEvent

HEADERS = {"X-Admin-Key": settings.admin_api_key}


def test_gumroad_purchase_creates_license(client, setup_db):
    r = client.post("/api/gumroad/webhook", headers=HEADERS, json={
        "email": "buyer@gumroad.com",
        "sale_id": "gum_sale_001",
        "product_id": "helpmeet_personal",
    })
    assert r.status_code == 200
    assert r.json()["ok"]


def test_gumroad_purchase_idempotent(client, db, setup_db):
    """Calling webhook twice with same sale_id must not create duplicate license."""
    payload = {
        "email": "buyer2@gumroad.com",
        "sale_id": "gum_sale_002",
        "product_id": "helpmeet_personal",
    }
    r1 = client.post("/api/gumroad/webhook", headers=HEADERS, json=payload)
    r2 = client.post("/api/gumroad/webhook", headers=HEADERS, json=payload)
    assert r1.json()["ok"] and r2.json()["ok"]
    # Only 1 license should exist for this customer
    customer = db.query(Customer).filter(Customer.email == "buyer2@gumroad.com").first()
    count = db.query(License).filter(License.customer_id == customer.id).count()
    assert count == 1


def test_gumroad_refund_revokes_license(client, db, setup_db):
    """Refund event marks license as refunded."""
    # Purchase first
    r = client.post("/api/gumroad/webhook", headers=HEADERS, json={
        "email": "buyer3@gumroad.com",
        "sale_id": "gum_sale_003",
        "product_id": "helpmeet_personal",
    })
    assert r.json()["ok"]

    # Refund
    r2 = client.post("/api/gumroad/webhook", headers=HEADERS, json={
        "email": "buyer3@gumroad.com",
        "sale_id": "gum_sale_003",
        "product_id": "helpmeet_personal",
        "refunded": True,
    })
    assert r2.json()["ok"]

    # Verify license status actually changed to "refunded"
    db.expire_all()
    customer = db.query(Customer).filter(Customer.email == "buyer3@gumroad.com").first()
    lic = db.query(License).filter(License.customer_id == customer.id).first()
    assert lic.status == "refunded"


def test_gumroad_no_admin_key(client, setup_db):
    r = client.post("/api/gumroad/webhook", json={
        "email": "buyer4@gumroad.com",
        "sale_id": "gum_sale_004",
        "product_id": "helpmeet_personal",
    })
    assert r.status_code == 422 or r.status_code == 403
