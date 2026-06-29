import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Any
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
from helpmeet_licenses.config import settings

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 365


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def create_activation_token(
    license_id: int,
    device_id: str,
    plan: str,
    updates_until: date | None,
) -> str:
    """
    Returns a signed JWT. Note: `updates_until` in the decoded payload
    is an ISO-format string, not a `date` object — use `date.fromisoformat()`
    to convert it if needed.
    """
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "license_id": license_id,
        "device_id_hash": _hash(device_id),
        "plan": plan,
        "updates_until": updates_until.isoformat() if updates_until else None,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=TOKEN_EXPIRE_DAYS)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def verify_activation_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise ValueError("token_expired")
    except JWTError:
        raise ValueError("invalid_token")


def hash_key(key: str) -> str:
    return _hash(key)
