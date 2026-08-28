from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource, OpeningHours


class RoadServiceType(str, Enum):
    STATION_SERVICE = "station_service"
    GARAGE = "garage"
    MECANICIEN = "mecanicien"
    VULCANISATEUR = "vulcanisateur"
    DEPANNAGE = "depannage"
    REMORQUAGE = "remorquage"
    LAVAGE_AUTO = "lavage_auto"
    PIECES_AUTO = "pieces_auto"
    PARKING = "parking"
    BORNE_RECHARGE = "borne_recharge"


class RoadServiceStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class RoadService(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    type: RoadServiceType
    description: Optional[str] = None
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours] = []
    offers_24h: bool = False
    contact_phone: Optional[str] = None
    status: RoadServiceStatus = RoadServiceStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class BreakdownReportStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class BreakdownReport(BaseModel):
    """Signalement de panne par un usager (§12)."""
    id: Optional[str] = Field(default=None, alias="_id")
    reporter_id: str
    location: GeoPoint
    description: Optional[str] = None
    assigned_service_id: Optional[str] = None
    status: BreakdownReportStatus = BreakdownReportStatus.OPEN
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
