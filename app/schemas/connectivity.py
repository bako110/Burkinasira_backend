from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource
from app.models.connectivity import ConnectivityPointType, ConnectivityPointStatus


class CreateConnectivityPointRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    type: ConnectivityPointType
    operator: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    is_free: Optional[bool] = None
    offers_esim: bool = False
    contact_phone: Optional[str] = None


class UpdateConnectivityPointRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[ConnectivityPointType] = None
    operator: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    address: Optional[str] = None
    is_free: Optional[bool] = None
    offers_esim: Optional[bool] = None
    contact_phone: Optional[str] = None
    status: Optional[ConnectivityPointStatus] = None


class ConnectivityPointSummary(BaseModel):
    id: str
    name: str
    type: ConnectivityPointType
    operator: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    is_free: Optional[bool] = None
    offers_esim: bool


class ConnectivityPointDetail(BaseModel):
    id: str
    name: str
    type: ConnectivityPointType
    operator: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    is_free: Optional[bool] = None
    offers_esim: bool
    contact_phone: Optional[str] = None
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class ConnectivityPointListResponse(BaseModel):
    items: List[ConnectivityPointSummary]
    total: int
    page: int
    page_size: int
