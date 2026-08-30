from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource, OpeningHours


class EstablishmentType(str, Enum):
    RESTAURANT = "restaurant"
    MAQUIS = "maquis"
    CAFE = "cafe"
    STREET_FOOD = "street_food"
    ETABLISSEMENT_TOURISTIQUE = "etablissement_touristique"


class DietaryTag(str, Enum):
    FAMILLE = "famille"
    VEGETARIEN = "vegetarien"
    BUDGET = "budget"


class MenuItem(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    currency: str = "XOF"
    is_specialty: bool = False


class CuisineStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Restaurant(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    owner_id: str
    name: str
    type: EstablishmentType
    description: str
    cuisine_style: Optional[str] = None  # ex: "traditionnelle burkinabè"
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    photos: List[str] = []
    videos: List[str] = []
    photos_360: List[str] = []
    opening_hours: List[OpeningHours] = []
    menu: List[MenuItem] = []
    dietary_tags: List[DietaryTag] = []
    accepts_table_booking: bool = True
    offers_takeaway: bool = False
    offers_cooking_workshop: bool = False
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    average_rating: float = 0.0
    review_count: int = 0
    is_verified: bool = False
    status: CuisineStatus = CuisineStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
