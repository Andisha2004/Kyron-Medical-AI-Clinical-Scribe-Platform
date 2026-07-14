from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.models.encounter import Encounter
from app.db.models.note import Note
from app.db.models.user import User
from app.db.models.enums import UserRole
from app.db.session import get_db_session


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def _unauthorized(detail: str = "Authentication required.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _forbidden(detail: str = "You do not have permission to perform this action.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def require_authenticated_user(
    request: Request,
    session: AsyncSession = Depends(get_database_session),
) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise _unauthorized()

    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError as exc:
        raise _unauthorized("Authentication token has expired.") from exc
    except InvalidTokenError as exc:
        raise _unauthorized("Authentication token is invalid.") from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise _unauthorized("Authentication token is invalid.")

    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise _unauthorized("Authenticated user was not found.")

    if not user.is_active:
        raise _forbidden("Account is deactivated.")

    return user


async def require_provider(
    current_user: User = Depends(require_authenticated_user),
) -> User:
    if current_user.role != UserRole.PROVIDER:
        raise _forbidden()
    return current_user


async def require_admin(
    current_user: User = Depends(require_authenticated_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise _forbidden()
    return current_user


async def get_provider_owned_encounter(
    encounter_id: str,
    current_user: User = Depends(require_provider),
    session: AsyncSession = Depends(get_database_session),
) -> Encounter:
    encounter = await session.scalar(
        select(Encounter).where(
            Encounter.id == encounter_id,
            Encounter.provider_id == current_user.id,
        )
    )
    if encounter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")
    return encounter


async def get_accessible_encounter(
    encounter_id: str,
    current_user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_database_session),
) -> Encounter:
    query = select(Encounter).where(Encounter.id == encounter_id)
    if current_user.role == UserRole.PROVIDER:
        query = query.where(Encounter.provider_id == current_user.id)

    encounter = await session.scalar(query)
    if encounter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")
    return encounter


async def get_accessible_note(
    note_id: str,
    current_user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_database_session),
) -> Note:
    query = (
        select(Note)
        .join(Encounter, Note.encounter_id == Encounter.id)
        .where(Note.id == note_id)
    )
    if current_user.role == UserRole.PROVIDER:
        query = query.where(Encounter.provider_id == current_user.id)

    note = await session.scalar(query)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
    return note
