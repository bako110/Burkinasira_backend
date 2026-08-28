from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource, OpeningHours
from app.models.market import MarketPlaceType, MarketPlaceStatus, Promotion


class CreateMarketPlaceRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    type: MarketPlaceType
    description: Optional[str] = None
    products_sold: List[str] = []
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours] = []
    contact_phone: Optional[str] = None


class UpdateMarketPlaceRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[MarketPlaceType] = None
    description: Optional[str] = None
    products_sold: Optional[List[str]] = None
    region: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    address: Optional[str] = None
    opening_hours: Optional[List[OpeningHours]] = None
    promotions: Optional[List[Promotion]] = None
    contact_phone: Optional[str] = None
    status: Optional[MarketPlaceStatus] = None


class MarketPlaceSummary(BaseModel):
    id: str
    name: str
    type: MarketPlaceType
    region: str
    city: Optional[str] = None
    location: GeoPoint
    has_active_promotion: bool


class MarketPlaceDetail(BaseModel):
    id: str
    name: str
    type: MarketPlaceType
    description: Optional[str] = None
    products_sold: List[str]
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours]
    promotions: List[Promotion]
    contact_phone: Optional[str] = None
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class MarketPlaceListResponse(BaseModel):
    items: List[MarketPlaceSummary]
    total: int
    page: int
    page_size: int
