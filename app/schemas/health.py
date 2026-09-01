from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource, OpeningHours
from app.models.health import HealthFacilityType, HealthFacilityStatus


class CreateHealthFacilityRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    type: HealthFacilityType
    description: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours] = []
    is_on_duty: bool = False
    services: List[str] = []
    contact_phone: Optional[str] = None


class UpdateHealthFacilityRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[HealthFacilityType] = None
    description: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    address: Optional[str] = None
    opening_hours: Optional[List[OpeningHours]] = None
    is_on_duty: Optional[bool] = None
    services: Optional[List[str]] = None
    contact_phone: Optional[str] = None
    status: Optional[HealthFacilityStatus] = None


class HealthFacilitySummary(BaseModel):
    id: str
    name: str
    slug: str
    type: HealthFacilityType
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    is_on_duty: bool
    contact_phone: Optional[str] = None


class HealthFacilityDetail(BaseModel):
    id: str
    name: str
    slug: str
    type: HealthFacilityType
    description: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours]
    is_on_duty: bool
    services: List[str]
    contact_phone: Optional[str] = None
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class HealthFacilityListResponse(BaseModel):
    items: List[HealthFacilitySummary]
    total: int
    page: int
    page_size: int
