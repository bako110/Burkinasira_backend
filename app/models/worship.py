from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource


class WorshipPlaceType(str, Enum):
    MOSQUEE = "mosquee"
    EGLISE = "eglise"
    TEMPLE = "temple"
    LIEU_CULTE_TRADITIONNEL = "lieu_culte_traditionnel"
    AUTRE = "autre"


class WorshipPlaceStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PublicEvent(BaseModel):
    title: str
    description: Optional[str] = None
    date: Optional[datetime] = None


class WorshipPlace(BaseModel):
    """Lieu de culte ouvert au public (§21)."""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    type: WorshipPlaceType
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    public_events: List[PublicEvent] = []
    visiting_rules: Optional[str] = None
    status: WorshipPlaceStatus = WorshipPlaceStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
