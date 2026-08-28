from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint
from app.models.weather import WeatherAlertSeverity


class WeatherSnapshotResponse(BaseModel):
    id: str
    region: str
    location: Optional[GeoPoint] = None
    temperature_celsius: Optional[float] = None
    condition: Optional[str] = None
    rain_probability_percent: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    air_quality_index: Optional[float] = None
    forecast_date: datetime
    source: Optional[str] = None


class CreateWeatherSnapshotRequest(BaseModel):
    region: str
    location: Optional[GeoPoint] = None
    temperature_celsius: Optional[float] = None
    condition: Optional[str] = None
    rain_probability_percent: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    air_quality_index: Optional[float] = None
    forecast_date: datetime
    source: Optional[str] = None


class CreateWeatherAlertRequest(BaseModel):
    region: str
    title: str
    description: str
    severity: WeatherAlertSeverity = WeatherAlertSeverity.INFO


class UpdateWeatherAlertRequest(BaseModel):
    region: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[WeatherAlertSeverity] = None
    is_active: Optional[bool] = None


class WeatherAlertResponse(BaseModel):
    id: str
    region: str
    title: str
    description: str
    severity: WeatherAlertSeverity
    is_active: bool
    created_at: datetime


class SeasonalTipResponse(BaseModel):
    id: str
    season: str
    title: str
    content: str
