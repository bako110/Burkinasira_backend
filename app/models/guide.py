from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class GuideStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Certification(BaseModel):
    title: str
    issued_by: Optional[str] = None
    document_url: Optional[str] = None


class GuideProfile(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str  # référence vers app.models.user.User (role=guide)
    display_name: str
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    languages: List[str] = []
    specialties: List[str] = []
    regions_covered: List[str] = []
    provinces_covered: List[str] = []
    certifications: List[Certification] = []
    hourly_rate: Optional[float] = None
    daily_rate: Optional[float] = None
    currency: str = "XOF"
    is_verified: bool = False
    status: GuideStatus = GuideStatus.PENDING
    rejection_reason: Optional[str] = None
    average_rating: float = 0.0
    review_count: int = 0
    visits_completed: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class GuideAvailabilitySlot(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    guide_id: str
    date: str  # "YYYY-MM-DD"
    start_time: str  # "HH:MM"
    end_time: str  # "HH:MM"
    is_booked: bool = False

    class Config:
        populate_by_name = True
