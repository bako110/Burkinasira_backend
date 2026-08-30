from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.guide import GuideStatus, Certification


class CreateGuideProfileRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=150)
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


class UpdateGuideProfileRequest(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    languages: Optional[List[str]] = None
    specialties: Optional[List[str]] = None
    regions_covered: Optional[List[str]] = None
    provinces_covered: Optional[List[str]] = None
    certifications: Optional[List[Certification]] = None
    hourly_rate: Optional[float] = None
    daily_rate: Optional[float] = None
    currency: Optional[str] = None


class GuideSummary(BaseModel):
    id: str
    display_name: str
    photo_url: Optional[str] = None
    languages: List[str]
    specialties: List[str]
    regions_covered: List[str]
    provinces_covered: List[str] = []
    is_verified: bool
    average_rating: float
    review_count: int
    daily_rate: Optional[float] = None
    currency: str


class GuideDetail(BaseModel):
    id: str
    user_id: str
    display_name: str
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    languages: List[str]
    specialties: List[str]
    regions_covered: List[str]
    provinces_covered: List[str] = []
    certifications: List[Certification]
    hourly_rate: Optional[float] = None
    daily_rate: Optional[float] = None
    currency: str
    is_verified: bool
    status: GuideStatus
    rejection_reason: Optional[str] = None
    average_rating: float
    review_count: int
    visits_completed: int
    created_at: datetime
    updated_at: datetime


class RejectGuideRequest(BaseModel):
    reason: str = Field(..., min_length=3)


class GuideListResponse(BaseModel):
    items: List[GuideSummary]
    total: int
    page: int
    page_size: int


class AvailabilitySlotRequest(BaseModel):
    date: str = Field(..., description="Format YYYY-MM-DD")
    start_time: str = Field(..., description="Format HH:MM")
    end_time: str = Field(..., description="Format HH:MM")


class AvailabilitySlotResponse(BaseModel):
    id: str
    guide_id: str
    date: str
    start_time: str
    end_time: str
    is_booked: bool
