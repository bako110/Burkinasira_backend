from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource


class AccommodationType(str, Enum):
    HOTEL = "hotel"
    AUBERGE = "auberge"
    CAMPEMENT = "campement"
    MAISON_HOTES = "maison_hotes"
    RESIDENCE = "residence"
    HEBERGEMENT_HABITANT = "hebergement_habitant"
    HEBERGEMENT_COMMUNAUTAIRE = "hebergement_communautaire"


class HotelStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class RoomType(BaseModel):
    name: str
    capacity: int = 2
    price_per_night: float
    currency: str = "XOF"
    total_rooms: int = 1
    amenities: List[str] = []


class Offer(BaseModel):
    title: str
    description: Optional[str] = None
    discount_percent: Optional[float] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class Hotel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    owner_id: str
    name: str
    type: AccommodationType
    description: str
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    photos: List[str] = []
    amenities: List[str] = []
    room_types: List[RoomType] = []
    offers: List[Offer] = []
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    average_rating: float = 0.0
    review_count: int = 0
    is_verified: bool = False
    status: HotelStatus = HotelStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
