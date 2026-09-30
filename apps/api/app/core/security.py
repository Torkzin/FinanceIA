import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("dummy-password-used-only-for-timing-protection")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return password_hash.verify(password, encoded_hash)
    except Exception:
        return False


def create_access_token(*, user_id: UUID, company_id: UUID, role: str) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_in = settings.access_token_expire_minutes * 60
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "company_id": str(company_id),
        "role": role,
        "type": "access",
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(
        claims,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in


def decode_access_token(token: str) -> dict[str, Any]:
    claims = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )
    if claims.get("type") != "access":
        raise jwt.InvalidTokenError("Unexpected token type")
    return claims


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def digest_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
