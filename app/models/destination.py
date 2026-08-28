from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DestinationCategory(str, Enum):
    SITE_NATUREL = "site_naturel"
    SITE_HISTORIQUE = "site_historique"
    SITE_CULTUREL = "site_culturel"
    SITE_RELIGIEUX = "site_religieux"
    MUSEE = "musee"
    MONUMENT = "monument"
    VILLAGE_TOURISTIQUE = "village_touristique"
    MARCHE_ARTISANAL = "marche_artisanal"
    PARC = "parc"
    AUTRE = "autre"


class DestinationStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class GeoPoint(BaseModel):
    latitude: float
    longitude: float


class OpeningHours(BaseModel):
    day: str  # ex: "lundi"
    open_time: Optional[str] = None  # ex: "08:00"
    close_time: Optional[str] = None  # ex: "18:00"
    closed: bool = False


class Accessibility(BaseModel):
    wheelchair_accessible: Optional[bool] = None
    notes: Optional[str] = None


class DataSource(BaseModel):
    verified: bool = False
    source: Optional[str] = None
    last_updated_at: Optional[datetime] = None


class Destination(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    slug: str
    description: str
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
    average_rating: float = 0.0
    review_count: int = 0
    status: DestinationStatus = DestinationStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
