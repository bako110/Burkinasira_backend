from enum import Enum
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TripThemeType(str, Enum):
    BUDGET = "budget"
    DUREE = "duree"
    REGION = "region"
    CULTUREL = "culturel"
    NATURE = "nature"
    FAMILIAL = "familial"
    GASTRONOMIQUE = "gastronomique"
    AFFAIRES = "affaires"


class TripStatus(str, Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TripItemType(str, Enum):
    DESTINATION = "destination"
    HOTEL = "hotel"
    RESTAURANT = "restaurant"
    EXPERIENCE = "experience"
    EVENT = "event"
    GUIDE = "guide"
    TRANSPORT = "transport"
    AUTRE = "autre"


class TripDayItem(BaseModel):
    """Un élément du calendrier jour par jour."""
    time: Optional[str] = None  # "HH:MM"
    type: TripItemType
    reference_id: Optional[str] = None  # id de la destination/hôtel/etc. lié
    title: str
    notes: Optional[str] = None
    estimated_cost: Optional[float] = None


class TripDay(BaseModel):
    date: date
    items: List[TripDayItem] = []


class TripCollaborator(BaseModel):
    user_id: str
    can_edit: bool = False


class Trip(BaseModel):
    """Voyage planifié par un utilisateur (§25)."""
    id: Optional[str] = Field(default=None, alias="_id")
    owner_id: str
    title: str
    themes: List[TripThemeType] = []
    region: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget_estimate: Optional[float] = None
    currency: str = "XOF"
    days: List[TripDay] = []
    linked_booking_ids: List[str] = []
    collaborators: List[TripCollaborator] = []
    status: TripStatus = TripStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
