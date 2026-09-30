from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    digest_refresh_token,
    generate_refresh_token,
    verify_password,
)
from app.db.models import Company, RefreshToken, User


class AuthenticationError(Exception):
    """Raised when credentials or a refresh session cannot be trusted."""


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    user: User


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    user = await session.scalar(
        select(User)
        .join(Company)
        .where(
            func.lower(User.email) == normalized_email,
            User.is_active.is_(True),
            Company.is_active.is_(True),
        )
    )
    encoded_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_is_valid = verify_password(password, encoded_hash)
    if not user or not password_is_valid:
        raise AuthenticationError("Invalid email or password")
    return user


def build_refresh_session(user_id: UUID, family_id: UUID | None = None) -> tuple[RefreshToken, str]:
    now = datetime.now(UTC)
    raw_token = generate_refresh_token()
    record = RefreshToken(
        user_id=user_id,
        token_hash=digest_refresh_token(raw_token),
        family_id=family_id or uuid4(),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        created_at=now,
    )
    return record, raw_token


async def issue_token_pair(session: AsyncSession, user: User) -> TokenPair:
    refresh_record, raw_refresh_token = build_refresh_session(user.id)
    session.add(refresh_record)
    await session.commit()
    access_token, expires_in = create_access_token(
        user_id=user.id,
        company_id=user.company_id,
        role=user.role,
    )
    return TokenPair(access_token, raw_refresh_token, expires_in, user)


async def rotate_refresh_token(session: AsyncSession, raw_token: str) -> TokenPair:
    now = datetime.now(UTC)
    token_hash = digest_refresh_token(raw_token)
    record = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    )
    if not record:
        raise AuthenticationError("Invalid refresh token")

    if record.revoked_at is not None:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == record.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await session.commit()
        raise AuthenticationError("Refresh token reuse detected")

    if record.expires_at <= now:
        record.revoked_at = now
        await session.commit()
        raise AuthenticationError("Refresh token expired")

    user = await session.get(User, record.user_id)
    if not user or not user.is_active:
        record.revoked_at = now
        await session.commit()
        raise AuthenticationError("User is inactive")

    replacement, raw_replacement = build_refresh_session(user.id, record.family_id)
    session.add(replacement)
    await session.flush()
    record.revoked_at = now
    record.replaced_by_id = replacement.id
    await session.commit()

    access_token, expires_in = create_access_token(
        user_id=user.id,
        company_id=user.company_id,
        role=user.role,
    )
    return TokenPair(access_token, raw_replacement, expires_in, user)


async def revoke_refresh_family(session: AsyncSession, raw_token: str) -> None:
    record = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == digest_refresh_token(raw_token))
    )
    if not record:
        return
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == record.family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()
