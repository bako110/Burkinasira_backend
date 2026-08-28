from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint
from app.models.airport import AirportInfoCategory


class CreateAirportRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    iata_code: Optional[str] = None
    city: str
    region: str
    location: GeoPoint
    description: Optional[str] = None


class UpdateAirportRequest(BaseModel):
    name: Optional[str] = None
    iata_code: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    location: Optional[GeoPoint] = None
    description: Optional[str] = None


class AirportResponse(BaseModel):
    id: str
    name: str
    iata_code: Optional[str] = None
    city: str
    region: str
    location: GeoPoint
    description: Optional[str] = None


class CreateAirportInfoRequest(BaseModel):
    category: AirportInfoCategory
    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=5)


class UpdateAirportInfoRequest(BaseModel):
    category: Optional[AirportInfoCategory] = None
    title: Optional[str] = None
    content: Optional[str] = None


class AirportInfoResponse(BaseModel):
    id: str
    airport_id: str
    category: AirportInfoCategory
    title: str
    content: str
    updated_at: datetime


class CreateBorderCrossingRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    neighboring_country: str
    region: str
    location: Optional[GeoPoint] = None
    notes: Optional[str] = None


class UpdateBorderCrossingRequest(BaseModel):
    name: Optional[str] = None
    neighboring_country: Optional[str] = None
    region: Optional[str] = None
    location: Optional[GeoPoint] = None
    notes: Optional[str] = None


class BorderCrossingResponse(BaseModel):
    id: str
    name: str
    neighboring_country: str
    region: str
    location: Optional[GeoPoint] = None
    notes: Optional[str] = None
