import pytest
from helpmeet_licenses.config import settings

HEADERS = {"X-Admin-Key": settings.admin_api_key}

def test_create_customer(client):
    resp = client.post("/api/admin/customers",
        json={"email": "victor@test.com", "name": "Víctor"},
        headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "victor@test.com"
    assert "id" in data

def test_create_customer_unauthorized(client):
    resp = client.post("/api/admin/customers",
        json={"email": "x@test.com"},
        headers={"X-Admin-Key": "wrong"})
    assert resp.status_code == 403

def test_create_license(client):
    cust = client.post("/api/admin/customers",
        json={"email": "lic@test.com"}, headers=HEADERS).json()
    resp = client.post("/api/admin/licenses",
        json={"customer_id": cust["id"], "plan": "personal", "updates_until": "2027-06-28"},
        headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "license_key" in data
    assert data["license_key"].startswith("HM-")
    assert "key_last4" in data

def test_list_licenses(client, a_license):
    resp = client.get("/api/admin/licenses", headers=HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

def test_get_license_detail(client, a_license):
    lic_id = a_license["license"].id
    resp = client.get(f"/api/admin/licenses/{lic_id}", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == lic_id
    assert "activations" in data

def test_revoke_license(client, a_license):
    lic_id = a_license["license"].id
    resp = client.post(f"/api/admin/licenses/{lic_id}/revoke", headers=HEADERS)
    assert resp.json()["ok"] is True
    detail = client.get(f"/api/admin/licenses/{lic_id}", headers=HEADERS).json()
    assert detail["status"] == "revoked"
