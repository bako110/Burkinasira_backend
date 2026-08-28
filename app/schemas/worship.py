from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource
from app.models.worship import WorshipPlaceType, WorshipPlaceStatus, PublicEvent


class CreateWorshipPlaceRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    type: WorshipPlaceType
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    public_events: List[PublicEvent] = []
    visiting_rules: Optional[str] = None


class UpdateWorshipPlaceRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[WorshipPlaceType] = None
    region: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    address: Optional[str] = None
    public_events: Optional[List[PublicEvent]] = None
    visiting_rules: Optional[str] = None
    status: Optional[WorshipPlaceStatus] = None


class WorshipPlaceSummary(BaseModel):
    id: str
    name: str
    type: WorshipPlaceType
    region: str
    city: Optional[str] = None
    location: GeoPoint


class WorshipPlaceDetail(BaseModel):
    id: str
    name: str
    type: WorshipPlaceType
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    public_events: List[PublicEvent]
    visiting_rules: Optional[str] = None
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class WorshipPlaceListResponse(BaseModel):
    items: List[WorshipPlaceSummary]
    total: int
    page: int
    page_size: int
