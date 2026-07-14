from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database_session, require_authenticated_user
from app.core.config import get_settings
from app.db.models.user import User
from app.schemas.auth import (
    AuthenticatedUserResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()


def build_authenticated_user_response(user: User) -> AuthenticatedUserResponse:
    profile = user.provider_profile
    return AuthenticatedUserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        first_name=profile.first_name if profile else None,
        last_name=profile.last_name if profile else None,
    )


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_database_session),
) -> LoginResponse:
    result = await auth_service.authenticate_user(
        session,
        email=payload.email,
        password=payload.password,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not result.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    await session.refresh(result.user, ["provider_profile"])
    await auth_service.record_login(session, user=result.user)
    await session.commit()

    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=result.access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return LoginResponse(
        user=build_authenticated_user_response(result.user),
        message="Login successful.",
    )


@router.get("/me", response_model=AuthenticatedUserResponse)
async def current_user(
    user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_database_session),
) -> AuthenticatedUserResponse:
    user_with_profile = await session.scalar(select(User).where(User.id == user.id))
    if user_with_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    await session.refresh(user_with_profile, ["provider_profile"])
    return build_authenticated_user_response(user_with_profile)


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response) -> LogoutResponse:
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return LogoutResponse(message="Logout successful.")
