from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class PromotionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class ProPromotion(BaseModel):
    """Promotion créée par un professionnel pour son offre (§35)."""
    id: Optional[str] = Field(default=None, alias="_id")
    provider_id: str
    title: str
    description: Optional[str] = None
    discount_percent: Optional[float] = None
    applies_to_item_type: str  # ex: "hotel", "restaurant", "experience"
    applies_to_item_id: str
    valid_from: datetime
    valid_until: datetime
    status: PromotionStatus = PromotionStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class TeamMemberRole(str, Enum):
    OWNER = "owner"
    MANAGER = "manager"
    STAFF = "staff"


class TeamMember(BaseModel):
    """Membre d'équipe rattaché à un compte professionnel."""
    id: Optional[str] = Field(default=None, alias="_id")
    provider_id: str
    user_id: Optional[str] = None  # None si invitation en attente (pas encore de compte)
    email: str
    role: TeamMemberRole = TeamMemberRole.STAFF
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
