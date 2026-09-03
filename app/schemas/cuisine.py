from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource, OpeningHours
from app.models.cuisine import EstablishmentType, DietaryTag, MenuItem, CuisineStatus


class CreateRestaurantRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    type: EstablishmentType
    description: str = Field(..., min_length=10)
    cuisine_style: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    photos: List[str] = []
    videos: List[str] = []
    opening_hours: List[OpeningHours] = []
    menu: List[MenuItem] = []
    dietary_tags: List[DietaryTag] = []
    accepts_table_booking: bool = True
    offers_takeaway: bool = False
    offers_cooking_workshop: bool = False
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


class UpdateRestaurantRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[EstablishmentType] = None
    description: Optional[str] = None
    cuisine_style: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    address: Optional[str] = None
    photos: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    opening_hours: Optional[List[OpeningHours]] = None
    menu: Optional[List[MenuItem]] = None
    dietary_tags: Optional[List[DietaryTag]] = None
    accepts_table_booking: Optional[bool] = None
    offers_takeaway: Optional[bool] = None
    offers_cooking_workshop: Optional[bool] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    status: Optional[CuisineStatus] = None


class RestaurantSummary(BaseModel):
    id: str
    name: str
    slug: str
    type: EstablishmentType
    cuisine_style: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    photo: Optional[str] = None
    dietary_tags: List[DietaryTag]
    average_rating: float
    review_count: int


class RestaurantDetail(BaseModel):
    id: str
    owner_id: str
    name: str
    slug: str
    type: EstablishmentType
    description: str
    cuisine_style: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    photos: List[str]
    videos: List[str]
    opening_hours: List[OpeningHours]
    menu: List[MenuItem]
    dietary_tags: List[DietaryTag]
    accepts_table_booking: bool
    offers_takeaway: bool
    offers_cooking_workshop: bool
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    average_rating: float
    review_count: int
    is_verified: bool
    status: CuisineStatus
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class RestaurantListResponse(BaseModel):
    items: List[RestaurantSummary]
    total: int
    page: int
    page_size: int
