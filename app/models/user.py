from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class UserRole(str, Enum):
    TOURIST = "tourist"
    GUIDE = "guide"
    PROVIDER = "provider"
    MODERATOR = "moderator"
    ADMIN = "admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    # Optionnel : les comptes créés via "Connexion avec Google" n'ont pas de
    # mot de passe local (auth_provider = "google", google_sub renseigné).
    hashed_password: Optional[str] = None
    auth_provider: str = "password"
    google_sub: Optional[str] = None
    role: UserRole = UserRole.TOURIST
    status: UserStatus = UserStatus.ACTIVE
    is_verified: bool = False
    avatar_url: Optional[str] = None
    preferred_language: str = "fr"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "full_name": "Awa Traoré",
                "email": "awa.traore@example.com",
                "phone": "+22670000000",
                "role": "tourist",
            }
        }
