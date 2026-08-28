from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource


class ConnectivityPointType(str, Enum):
    OPERATEUR_TELECOM = "operateur_telecom"
    POINT_VENTE_SIM = "point_vente_sim"
    WIFI_PUBLIC = "wifi_public"
    WIFI_PRIVE = "wifi_prive"
    COWORKING = "coworking"
    BOUTIQUE_TELEPHONIE = "boutique_telephonie"


class ConnectivityPointStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ConnectivityPoint(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    type: ConnectivityPointType
    operator: Optional[str] = None  # ex: "Orange", "Moov Africa", "Telecel"
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    is_free: Optional[bool] = None  # pour le Wi-Fi
    offers_esim: bool = False
    contact_phone: Optional[str] = None
    status: ConnectivityPointStatus = ConnectivityPointStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
