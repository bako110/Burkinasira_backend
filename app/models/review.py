from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ReviewTargetType(str, Enum):
    GUIDE = "guide"
    HOTEL = "hotel"
    RESTAURANT = "restaurant"
    TRANSPORT = "transport"
    DESTINATION = "destination"
    EVENT = "event"
    ARTISAN_PRODUCT = "artisan_product"


class ReviewStatus(str, Enum):
    PUBLISHED = "published"
    FLAGGED = "flagged"
    HIDDEN = "hidden"


class ReviewReplyReportReason(str, Enum):
    SPAM = "spam"
    ABUSIVE = "abusive"
    FAKE = "fake"
    OFF_TOPIC = "off_topic"
    AUTRE = "autre"


class ReviewReport(BaseModel):
    reporter_id: str
    reason: ReviewReplyReportReason
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Review(BaseModel):
    """Avis client vérifié — lié à une réservation complétée pour éviter les faux avis (§37)."""
    id: Optional[str] = Field(default=None, alias="_id")
    target_type: ReviewTargetType
    target_id: str
    author_id: str
    booking_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)
    photos: List[str] = []
    reply_comment: Optional[str] = None
    reply_at: Optional[datetime] = None
    status: ReviewStatus = ReviewStatus.PUBLISHED
    reports: List[ReviewReport] = []
    helpful_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class ReviewAggregate(BaseModel):
    """Statistiques agrégées pour une cible donnée (mis en cache sur le profil correspondant)."""
    target_type: ReviewTargetType
    target_id: str
    average_rating: float = 0.0
    review_count: int = 0
    rating_breakdown: dict = Field(default_factory=lambda: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0})
