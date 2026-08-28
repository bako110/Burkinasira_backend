from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint


class WeatherAlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class WeatherSnapshot(BaseModel):
    """Relevé météo courant/prévision pour une région (§24)."""
    id: Optional[str] = Field(default=None, alias="_id")
    region: str
    location: Optional[GeoPoint] = None
    temperature_celsius: Optional[float] = None
    condition: Optional[str] = None  # ex: "ensoleillé", "pluvieux"
    rain_probability_percent: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    air_quality_index: Optional[float] = None
    forecast_date: datetime
    source: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class WeatherAlert(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    region: str
    title: str
    description: str
    severity: WeatherAlertSeverity = WeatherAlertSeverity.INFO
    is_active: bool = True
    published_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class SeasonalTip(BaseModel):
    """Conseils de préparation selon la saison."""
    id: Optional[str] = Field(default=None, alias="_id")
    season: str  # ex: "saison sèche", "saison des pluies"
    title: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
