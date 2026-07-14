from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.db.models.user import User
from app.services.audit_service import AuditService


@dataclass
class AuthenticationResult:
    user: User
    access_token: str


class AuthService:
    def __init__(self) -> None:
        self.audit_service = AuditService()

    async def authenticate_user(
        self,
        session: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> AuthenticationResult | None:
        normalized_email = email.strip().lower()
        user = await session.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            return None

        if not verify_password(password, user.password_hash):
            return None

        access_token = create_access_token(user.id)
        return AuthenticationResult(user=user, access_token=access_token)

    async def record_login(self, session: AsyncSession, *, user: User) -> None:
        await self.audit_service.log_event(
            session,
            actor_user_id=user.id,
            action="USER_LOGIN",
            entity_type="user",
            entity_id=user.id,
            metadata={"role": user.role.value},
        )
