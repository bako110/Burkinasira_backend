from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint
from app.models.mobility import TransportType, TripRequestStatus, TransportProviderStatus


class CreateTransportProviderRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    type: TransportType
    description: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    base_location: Optional[GeoPoint] = None
    vehicle_info: Optional[str] = None
    photos: List[str] = []
    videos: List[str] = []
    price_estimate: Optional[float] = None
    price_currency: str = "XOF"
    contact_phone: str


class UpdateTransportProviderRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    base_location: Optional[GeoPoint] = None
    vehicle_info: Optional[str] = None
    photos: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    price_estimate: Optional[float] = None
    price_currency: Optional[str] = None
    contact_phone: Optional[str] = None


class TransportProviderSummary(BaseModel):
    id: str
    name: str
    slug: str
    type: TransportType
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    photo: Optional[str] = None
    price_estimate: Optional[float] = None
    price_currency: str
    is_verified: bool
    average_rating: float
    review_count: int


class TransportProviderDetail(BaseModel):
    id: str
    owner_id: str
    name: str
    slug: str
    type: TransportType
    description: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    base_location: Optional[GeoPoint] = None
    vehicle_info: Optional[str] = None
    photos: List[str]
    videos: List[str]
    price_estimate: Optional[float] = None
    price_currency: str
    contact_phone: str
    is_verified: bool
    status: TransportProviderStatus
    average_rating: float
    review_count: int
    created_at: datetime
    updated_at: datetime


class TransportProviderListResponse(BaseModel):
    items: List[TransportProviderSummary]
    total: int
    page: int
    page_size: int


class CreateTripRequest(BaseModel):
    provider_id: str
    type: TransportType
    pickup_location: GeoPoint
    pickup_address: Optional[str] = None
    dropoff_location: Optional[GeoPoint] = None
    dropoff_address: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class TripRequestResponse(BaseModel):
    id: str
    passenger_id: str
    provider_id: str
    type: TransportType
    pickup_location: GeoPoint
    pickup_address: Optional[str] = None
    dropoff_location: Optional[GeoPoint] = None
    dropoff_address: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    estimated_price: Optional[float] = None
    price_currency: str
    status: TripRequestStatus
    created_at: datetime


class UpdateTripStatusRequest(BaseModel):
    status: TripRequestStatus
