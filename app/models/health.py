from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource, OpeningHours


class HealthFacilityType(str, Enum):
    PHARMACIE = "pharmacie"
    HOPITAL = "hopital"
    CLINIQUE = "clinique"
    LABORATOIRE = "laboratoire"
    CENTRE_PREMIERS_SECOURS = "centre_premiers_secours"
    DENTISTE = "dentiste"
    AUTRE = "autre"


class HealthFacilityStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class HealthFacility(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    type: HealthFacilityType
    description: Optional[str] = None
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours] = []
    is_on_duty: bool = False  # pharmacie de garde
    services: List[str] = []
    contact_phone: Optional[str] = None
    status: HealthFacilityStatus = HealthFacilityStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
