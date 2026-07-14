from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=255)


class AuthenticatedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: UserRole
    is_active: bool
    first_name: str | None = None
    last_name: str | None = None


class LoginResponse(BaseModel):
    user: AuthenticatedUserResponse
    message: str


class LogoutResponse(BaseModel):
    message: str
