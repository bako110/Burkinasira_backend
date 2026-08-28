from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource
from app.models.family import FamilyServiceType, FamilyServiceStatus


class CreateFamilyServiceRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    type: FamilyServiceType
    description: Optional[str] = None
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    is_family_friendly: bool = True
    contact_phone: Optional[str] = None


class UpdateFamilyServiceRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[FamilyServiceType] = None
    description: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    address: Optional[str] = None
    is_family_friendly: Optional[bool] = None
    contact_phone: Optional[str] = None
    status: Optional[FamilyServiceStatus] = None


class FamilyServiceSummary(BaseModel):
    id: str
    name: str
    type: FamilyServiceType
    region: str
    city: Optional[str] = None
    location: GeoPoint
    is_family_friendly: bool


class FamilyServiceDetail(BaseModel):
    id: str
    name: str
    type: FamilyServiceType
    description: Optional[str] = None
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    is_family_friendly: bool
    is_verified_provider: bool
    contact_phone: Optional[str] = None
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class FamilyServiceListResponse(BaseModel):
    items: List[FamilyServiceSummary]
    total: int
    page: int
    page_size: int


class BookChildcareRequest(BaseModel):
    service_id: str
    requested_date: datetime
    notes: Optional[str] = None


class ChildcareBookingResponse(BaseModel):
    id: str
    service_id: str
    parent_id: str
    requested_date: datetime
    notes: Optional[str] = None
    status: str
    created_at: datetime
