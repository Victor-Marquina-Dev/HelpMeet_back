def test_activate_valid_key(client, a_license):
    resp = client.post("/api/license/activate", json={
        "license_key": a_license["key"],
        "device_id": "device-abc",
        "device_name": "PC Test",
        "app_version": "1.2.7",
        "os": "Windows 11",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "activation_token" in data
    assert data["plan"] == "personal"

def test_activate_unknown_key(client):
    resp = client.post("/api/license/activate", json={
        "license_key": "HM-0000-0000-0000-0000",
        "device_id": "device-abc",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert resp.json()["error"] == "license_not_found"

def test_activate_revoked_key(client, a_license, db):
    from helpmeet_licenses.models import License
    lic = db.get(License, a_license["license"].id)
    lic.status = "revoked"
    db.commit()
    resp = client.post("/api/license/activate", json={
        "license_key": a_license["key"],
        "device_id": "device-abc",
    })
    assert resp.json()["error"] == "license_revoked"

def test_validate_valid_token(client, a_license):
    activate = client.post("/api/license/activate", json={
        "license_key": a_license["key"],
        "device_id": "device-abc",
    }).json()
    resp = client.post("/api/license/validate", json={
        "activation_token": activate["activation_token"],
        "device_id": "device-abc",
    })
    assert resp.json()["ok"] is True
    assert resp.json()["status"] == "active"

def test_validate_bad_token(client):
    resp = client.post("/api/license/validate", json={
        "activation_token": "not-a-jwt",
        "device_id": "device-abc",
    })
    assert resp.json()["error"] == "invalid_token"

def test_deactivate(client, a_license):
    token = client.post("/api/license/activate", json={
        "license_key": a_license["key"],
        "device_id": "device-abc",
    }).json()["activation_token"]
    resp = client.post("/api/license/deactivate", json={
        "activation_token": token,
        "device_id": "device-abc",
    })
    assert resp.json()["ok"] is True
