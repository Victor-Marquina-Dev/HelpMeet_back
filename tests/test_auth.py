import pytest
from datetime import date
from helpmeet_licenses.auth import create_activation_token, verify_activation_token


def test_create_and_verify_token():
    token = create_activation_token(
        license_id=1,
        device_id="my-device-123",
        plan="personal",
        updates_until=date(2027, 6, 28),
    )
    assert isinstance(token, str)
    payload = verify_activation_token(token)
    assert payload["license_id"] == 1
    assert payload["plan"] == "personal"
    assert "device_id_hash" in payload


def test_invalid_token_raises():
    with pytest.raises(ValueError, match="invalid_token"):
        verify_activation_token("not-a-valid-token")
