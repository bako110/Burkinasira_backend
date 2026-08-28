from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint


class AirportInfoCategory(str, Enum):
    HORAIRES = "horaires"
    TRANSPORT = "transport"
    CHANGE = "change"
    CONNECTIVITE = "connectivite"
    FORMALITES = "formalites"
    CONTACTS_UTILES = "contacts_utiles"
    FRONTIERE = "frontiere"


class Airport(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    iata_code: Optional[str] = None
    city: str
    region: str
    location: GeoPoint
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class AirportInfo(BaseModel):
    """Bloc d'information rattaché à un aéroport (horaires, transport, formalités...)."""
    id: Optional[str] = Field(default=None, alias="_id")
    airport_id: str
    category: AirportInfoCategory
    title: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class BorderCrossing(BaseModel):
    """Point de sortie / frontière terrestre publié."""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    neighboring_country: str
    region: str
    location: Optional[GeoPoint] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
