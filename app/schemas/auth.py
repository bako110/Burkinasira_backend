import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.user import UserRole


def _validate_password_strength(v: str) -> str:
    if not re.search(r"[A-Z]", v):
        raise ValueError("Le mot de passe doit contenir au moins une majuscule")
    if not re.search(r"[0-9]", v):
        raise ValueError("Le mot de passe doit contenir au moins un chiffre")
    return v


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.TOURIST

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)

    @field_validator("role")
    @classmethod
    def restrict_self_signup_role(cls, v: UserRole) -> UserRole:
        if v in (UserRole.ADMIN, UserRole.MODERATOR):
            raise ValueError("Ce rôle ne peut pas être choisi à l'inscription")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GuestSessionRequest(BaseModel):
    device_id: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    preferred_language: Optional[str] = None


class UserPublic(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole
    is_verified: bool
    avatar_url: Optional[str] = None
    preferred_language: str
    created_at: datetime


class UserVerification(BaseModel):
    """Informations minimales exposées publiquement pour vérifier l'identité
    d'un porteur de carte FasoViva (via le QR code) — pas d'email, pas de
    téléphone, pas d'identifiant technique (ObjectId)."""
    full_name: str
    role: UserRole
    is_verified: bool
    avatar_url: Optional[str] = None
    member_since: datetime


class TokenPayload(BaseModel):
    sub: str
    email: EmailStr
    role: UserRole
    permissions: List[str] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserPublic
