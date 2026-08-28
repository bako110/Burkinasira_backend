from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint


class EduOutingType(str, Enum):
    VISITE_HISTORIQUE = "visite_historique"
    VISITE_CULTURELLE = "visite_culturelle"
    VISITE_SCIENTIFIQUE = "visite_scientifique"
    VISITE_AGRICOLE = "visite_agricole"
    VISITE_INDUSTRIELLE = "visite_industrielle"
    EXCURSION_UNIVERSITAIRE = "excursion_universitaire"


class EduOutingStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EducationalOuting(BaseModel):
    """Sortie scolaire ou universitaire (§30)."""
    id: Optional[str] = Field(default=None, alias="_id")
    organizer_id: str
    title: str
    type: EduOutingType
    description: str
    region: str
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    target_level: Optional[str] = None  # ex: "collège", "lycée", "université"
    price_per_participant: Optional[float] = None
    currency: str = "XOF"
    max_participants: Optional[int] = None
    status: EduOutingStatus = EduOutingStatus.PUBLISHED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class EduBookingStatus(str, Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class EduBooking(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    outing_id: str
    booked_by: str
    group_name: str
    participant_count: int = Field(gt=0)
    status: EduBookingStatus = EduBookingStatus.REQUESTED
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class EduParticipant(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    booking_id: str
    full_name: str
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
