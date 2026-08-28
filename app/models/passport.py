from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class BadgeCategory(str, Enum):
    DECOUVERTE = "decouverte"
    CULTURE = "culture"
    GASTRONOMIE = "gastronomie"
    NATURE = "nature"
    COMMUNAUTE = "communaute"
    FIDELITE = "fidelite"


class Badge(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: str
    category: BadgeCategory
    icon_url: Optional[str] = None
    criteria: Optional[str] = None  # description humaine du critère d'obtention
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class ChallengeStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Challenge(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    description: str
    target_count: int = 1  # ex: visiter 5 destinations
    related_category: Optional[str] = None
    reward_badge_id: Optional[str] = None
    status: ChallengeStatus = ChallengeStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class Stamp(BaseModel):
    """Tampon numérique collecté pour une destination visitée."""
    destination_id: str
    destination_name: str
    collected_at: datetime = Field(default_factory=datetime.utcnow)


class UserChallengeProgress(BaseModel):
    challenge_id: str
    current_count: int = 0
    completed: bool = False
    completed_at: Optional[datetime] = None


class TravelPassport(BaseModel):
    """Passeport numérique GoTours de l'utilisateur (§28)."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    stamps: List[Stamp] = []
    earned_badge_ids: List[str] = []
    challenge_progress: List[UserChallengeProgress] = []
    points: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
