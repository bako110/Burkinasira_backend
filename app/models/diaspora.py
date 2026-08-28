from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint


class DiasporaContentType(str, Enum):
    CIRCUIT_CULTUREL = "circuit_culturel"
    PATRIMOINE_FAMILIAL = "patrimoine_familial"
    HEBERGEMENT = "hebergement"
    TRANSPORT = "transport"
    EVENEMENT_CULTUREL = "evenement_culturel"
    SERVICE_VISITEUR_RETOUR = "service_visiteur_retour"


class DiasporaContent(BaseModel):
    """Contenu dédié au parcours diaspora / tourisme de retour (§31)."""
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    type: DiasporaContentType
    description: str
    region: Optional[str] = None
    location: Optional[GeoPoint] = None
    related_destination_id: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class CommunityMeetupStatus(str, Enum):
    PLANNED = "planned"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class CommunityMeetup(BaseModel):
    """Rencontre communautaire proposée aux visiteurs de la diaspora."""
    id: Optional[str] = Field(default=None, alias="_id")
    organizer_id: str
    title: str
    description: Optional[str] = None
    region: str
    location: Optional[GeoPoint] = None
    scheduled_at: datetime
    status: CommunityMeetupStatus = CommunityMeetupStatus.PLANNED
    participant_ids: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
