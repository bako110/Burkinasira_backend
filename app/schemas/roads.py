from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource, OpeningHours
from app.models.roads import RoadServiceType, RoadServiceStatus, BreakdownReportStatus


class CreateRoadServiceRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    type: RoadServiceType
    description: Optional[str] = None
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours] = []
    offers_24h: bool = False
    contact_phone: Optional[str] = None


class UpdateRoadServiceRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[RoadServiceType] = None
    description: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    address: Optional[str] = None
    opening_hours: Optional[List[OpeningHours]] = None
    offers_24h: Optional[bool] = None
    contact_phone: Optional[str] = None
    status: Optional[RoadServiceStatus] = None


class RoadServiceSummary(BaseModel):
    id: str
    name: str
    type: RoadServiceType
    region: str
    city: Optional[str] = None
    location: GeoPoint
    offers_24h: bool
    contact_phone: Optional[str] = None


class RoadServiceDetail(BaseModel):
    id: str
    name: str
    type: RoadServiceType
    description: Optional[str] = None
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours]
    offers_24h: bool
    contact_phone: Optional[str] = None
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class RoadServiceListResponse(BaseModel):
    items: List[RoadServiceSummary]
    total: int
    page: int
    page_size: int


class ReportBreakdownRequest(BaseModel):
    location: GeoPoint
    description: Optional[str] = None


class BreakdownReportResponse(BaseModel):
    id: str
    reporter_id: str
    location: GeoPoint
    description: Optional[str] = None
    assigned_service_id: Optional[str] = None
    status: BreakdownReportStatus
    created_at: datetime


class AssignBreakdownRequest(BaseModel):
    service_id: str
