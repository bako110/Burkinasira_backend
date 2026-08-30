from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource
from app.models.hotel import AccommodationType, HotelStatus, RoomType, Offer


class CreateHotelRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    type: AccommodationType
    description: str = Field(..., min_length=10)
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    photos: List[str] = []
    videos: List[str] = []
    photos_360: List[str] = []
    amenities: List[str] = []
    room_types: List[RoomType] = []
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


class UpdateHotelRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[AccommodationType] = None
    description: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    address: Optional[str] = None
    photos: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    photos_360: Optional[List[str]] = None
    amenities: Optional[List[str]] = None
    room_types: Optional[List[RoomType]] = None
    offers: Optional[List[Offer]] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    status: Optional[HotelStatus] = None


class HotelSummary(BaseModel):
    id: str
    name: str
    type: AccommodationType
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    photo: Optional[str] = None
    min_price: Optional[float] = None
    currency: str = "XOF"
    average_rating: float
    review_count: int
    is_verified: bool


class HotelDetail(BaseModel):
    id: str
    owner_id: str
    name: str
    type: AccommodationType
    description: str
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    photos: List[str]
    videos: List[str]
    photos_360: List[str]
    amenities: List[str]
    room_types: List[RoomType]
    offers: List[Offer]
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    average_rating: float
    review_count: int
    is_verified: bool
    status: HotelStatus
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class HotelListResponse(BaseModel):
    items: List[HotelSummary]
    total: int
    page: int
    page_size: int


class AvailabilityCheckRequest(BaseModel):
    check_in: date
    check_out: date
    room_type_name: Optional[str] = None


class RoomAvailability(BaseModel):
    room_type_name: str
    total_rooms: int
    booked_rooms: int
    available_rooms: int
    price_per_night: float
    currency: str


class AvailabilityCheckResponse(BaseModel):
    check_in: date
    check_out: date
    rooms: List[RoomAvailability]
