"""Auth request/response schemas (Pydantic v2)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    """Step 1: request a reset email for the given address."""

    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Step 2: complete the reset using the token from the emailed link."""

    reset_token: str
    new_password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    """Supabase Auth session tokens returned on successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserRead(BaseModel):
    """Identity + profile view returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: str | None = None
    created_at: datetime
