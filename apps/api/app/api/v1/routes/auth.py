from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.api.dependencies.auth import CurrentUser, SessionDependency, require_roles
from app.core.config import settings
from app.db.models import User
from app.db.models.enums import UserRole
from app.schemas.auth import AuthenticatedUser, LoginRequest, MessageResponse, TokenResponse
from app.services.auth import (
    AuthenticationError,
    TokenPair,
    authenticate_user,
    issue_token_pair,
    revoke_refresh_family,
    rotate_refresh_token,
)

router = APIRouter()


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/api/v1/auth",
    )


def token_response(pair: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        expires_in=pair.expires_in,
        user=AuthenticatedUser.model_validate(pair.user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: SessionDependency,
) -> TokenResponse:
    try:
        user = await authenticate_user(session, str(payload.email), payload.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    pair = await issue_token_pair(session, user)
    set_refresh_cookie(response, pair.refresh_token)
    return token_response(pair)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: SessionDependency,
) -> TokenResponse:
    raw_token = request.cookies.get(settings.refresh_cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token"
        )
    try:
        pair = await rotate_refresh_token(session, raw_token)
    except AuthenticationError as exc:
        response.delete_cookie(key=settings.refresh_cookie_name, path="/api/v1/auth")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    set_refresh_cookie(response, pair.refresh_token)
    return token_response(pair)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    session: SessionDependency,
) -> MessageResponse:
    raw_token = request.cookies.get(settings.refresh_cookie_name)
    if raw_token:
        await revoke_refresh_family(session, raw_token)
    response.delete_cookie(key=settings.refresh_cookie_name, path="/api/v1/auth")
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=AuthenticatedUser)
async def me(current_user: CurrentUser) -> AuthenticatedUser:
    return AuthenticatedUser.model_validate(current_user)


@router.get("/users", response_model=list[AuthenticatedUser])
async def list_company_users(
    admin: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    session: SessionDependency,
) -> list[AuthenticatedUser]:
    users = await session.scalars(
        select(User).where(User.company_id == admin.company_id).order_by(User.full_name)
    )
    return [AuthenticatedUser.model_validate(user) for user in users]
