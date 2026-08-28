from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource
from app.models.experience import ExperienceType, ExperienceStatus, RevenueShare


class CreateExperienceRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=10)
    type: ExperienceType
    region: str
    city: Optional[str] = None
    location: GeoPoint
    photos: List[str] = []
    duration_minutes: Optional[int] = None
    max_participants: Optional[int] = None
    price_amount: Optional[float] = None
    price_currency: str = "XOF"
    languages: List[str] = []
    revenue_share: Optional[RevenueShare] = None


class UpdateExperienceRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[ExperienceType] = None
    region: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    photos: Optional[List[str]] = None
    duration_minutes: Optional[int] = None
    max_participants: Optional[int] = None
    price_amount: Optional[float] = None
    price_currency: Optional[str] = None
    languages: Optional[List[str]] = None
    revenue_share: Optional[RevenueShare] = None
    status: Optional[ExperienceStatus] = None


class ExperienceSummary(BaseModel):
    id: str
    title: str
    type: ExperienceType
    host_name: str
    region: str
    city: Optional[str] = None
    photo: Optional[str] = None
    price_amount: Optional[float] = None
    price_currency: str
    average_rating: float
    review_count: int


class ExperienceDetail(BaseModel):
    id: str
    title: str
    description: str
    type: ExperienceType
    host_id: str
    host_name: str
    region: str
    city: Optional[str] = None
    location: GeoPoint
    photos: List[str]
    duration_minutes: Optional[int] = None
    max_participants: Optional[int] = None
    price_amount: Optional[float] = None
    price_currency: str
    languages: List[str]
    revenue_share: Optional[RevenueShare] = None
    average_rating: float
    review_count: int
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class ExperienceListResponse(BaseModel):
    items: List[ExperienceSummary]
    total: int
    page: int
    page_size: int
