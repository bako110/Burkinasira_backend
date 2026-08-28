from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource


class EventCategory(str, Enum):
    FESTIVAL = "festival"
    CONCERT = "concert"
    FOIRE = "foire"
    EXPOSITION = "exposition"
    CULTUREL = "culturel"
    SPORTIF = "sportif"
    GASTRONOMIQUE = "gastronomique"
    CEREMONIE_TRADITIONNELLE = "ceremonie_traditionnelle"
    CONFERENCE = "conference"
    SALON = "salon"


class EventStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ProgramItem(BaseModel):
    time: Optional[str] = None  # "HH:MM"
    title: str
    description: Optional[str] = None


class Event(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    organizer_id: str
    title: str
    description: str
    category: EventCategory
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    photos: List[str] = []
    start_date: datetime
    end_date: Optional[datetime] = None
    program: List[ProgramItem] = []
    ticket_price: Optional[float] = None
    currency: str = "XOF"
    requires_ticket: bool = False
    linked_hotel_ids: List[str] = []
    linked_transport_provider_ids: List[str] = []
    status: EventStatus = EventStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
