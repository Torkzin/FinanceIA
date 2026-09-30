from collections.abc import Callable
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models import Company, User
from app.db.models.enums import UserRole
from app.db.session import get_session

bearer_scheme = HTTPBearer(auto_error=False)
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDependency,
) -> User:
    if not credentials:
        raise unauthorized()
    try:
        claims: dict[str, Any] = decode_access_token(credentials.credentials)
        user_id = UUID(claims["sub"])
        company_id = UUID(claims["company_id"])
    except (KeyError, TypeError, ValueError, jwt.InvalidTokenError) as exc:
        raise unauthorized() from exc

    user = await session.scalar(
        select(User)
        .join(Company)
        .where(
            User.id == user_id,
            User.company_id == company_id,
            User.is_active.is_(True),
            Company.is_active.is_(True),
        )
    )
    if not user:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: UserRole) -> Callable[..., User]:
    allowed_values = {role.value for role in allowed_roles}

    async def role_dependency(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_dependency
