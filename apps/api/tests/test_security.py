from uuid import uuid4

import jwt

from app.core.security import (
    create_access_token,
    decode_access_token,
    digest_refresh_token,
    generate_refresh_token,
    hash_password,
    verify_password,
)


def test_password_is_argon2_hashed_and_verifiable() -> None:
    encoded = hash_password("StrongDemoPassword123!")

    assert encoded.startswith("$argon2")
    assert verify_password("StrongDemoPassword123!", encoded)
    assert not verify_password("wrong-password", encoded)
    assert not verify_password("StrongDemoPassword123!", "!invalid-placeholder")


def test_access_token_contains_tenant_and_role_claims() -> None:
    user_id = uuid4()
    company_id = uuid4()

    token, expires_in = create_access_token(
        user_id=user_id,
        company_id=company_id,
        role="admin",
    )
    claims = decode_access_token(token)

    assert claims["sub"] == str(user_id)
    assert claims["company_id"] == str(company_id)
    assert claims["role"] == "admin"
    assert claims["type"] == "access"
    assert expires_in == 15 * 60


def test_refresh_tokens_are_random_and_only_digests_match() -> None:
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first != second
    assert len(digest_refresh_token(first)) == 64
    assert digest_refresh_token(first) != digest_refresh_token(second)


def test_non_access_jwt_is_rejected() -> None:
    from app.core.config import settings

    token = jwt.encode(
        {"type": "refresh"},
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    try:
        decode_access_token(token)
    except jwt.InvalidTokenError:
        pass
    else:
        raise AssertionError("A non-access token must not be accepted")
