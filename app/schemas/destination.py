from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import (
    DestinationCategory,
    DestinationStatus,
    GeoPoint,
    OpeningHours,
    Accessibility,
    DataSource,
)


class CreateDestinationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=10)
    category: DestinationCategory
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    photos: List[str] = []
    videos: List[str] = []
    opening_hours: List[OpeningHours] = []
    price_info: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    booking_url: Optional[str] = None
    services_on_site: List[str] = []
    accessibility: Accessibility = Accessibility()
    history: Optional[str] = None


class UpdateDestinationRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[DestinationCategory] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    address: Optional[str] = None
    photos: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    opening_hours: Optional[List[OpeningHours]] = None
    price_info: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    booking_url: Optional[str] = None
    services_on_site: Optional[List[str]] = None
    accessibility: Optional[Accessibility] = None
    history: Optional[str] = None
    status: Optional[DestinationStatus] = None


class DestinationSummary(BaseModel):
    """Utilisé pour l'affichage liste/carte (Explorer)."""
    id: str
    name: str
    slug: str
    category: DestinationCategory
    region: str
    city: Optional[str] = None
    location: GeoPoint
    photo: Optional[str] = None
    average_rating: float
    review_count: int
    price_info: Optional[str] = None


class DestinationDetail(BaseModel):
    """Utilisé pour la fiche complète d'un lieu (§4)."""
    id: str
    name: str
    slug: str
    description: str
    category: DestinationCategory
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    photos: List[str]
    videos: List[str]
    opening_hours: List[OpeningHours]
    price_info: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    booking_url: Optional[str] = None
    services_on_site: List[str]
    accessibility: Accessibility
    history: Optional[str] = None
    average_rating: float
    review_count: int
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class DestinationListResponse(BaseModel):
    items: List[DestinationSummary]
    total: int
    page: int
    page_size: int
