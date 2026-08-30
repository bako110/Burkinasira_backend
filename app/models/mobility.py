from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint


class TransportType(str, Enum):
    TAXI_VTC = "taxi_vtc"
    CHAUFFEUR_PRIVE = "chauffeur_prive"
    LOCATION_VOITURE = "location_voiture"
    LOCATION_MOTO = "location_moto"
    TRANSPORT_INTERURBAIN = "transport_interurbain"
    TRANSFERT_AEROPORT = "transfert_aeroport"
    TRANSPORT_TOURISTIQUE_PRIVE = "transport_touristique_prive"


class TransportProviderStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class TransportProvider(BaseModel):
    """Chauffeur, société de transport ou loueur référencé."""
    id: Optional[str] = Field(default=None, alias="_id")
    owner_id: str
    name: str
    type: TransportType
    description: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    base_location: Optional[GeoPoint] = None
    vehicle_info: Optional[str] = None
    price_estimate: Optional[float] = None
    price_currency: str = "XOF"
    contact_phone: str
    is_verified: bool = False
    status: TransportProviderStatus = TransportProviderStatus.PENDING
    average_rating: float = 0.0
    review_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class TripRequestStatus(str, Enum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TripRequest(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    passenger_id: str
    provider_id: str
    type: TransportType
    pickup_location: GeoPoint
    pickup_address: Optional[str] = None
    dropoff_location: Optional[GeoPoint] = None
    dropoff_address: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    estimated_price: Optional[float] = None
    price_currency: str = "XOF"
    status: TripRequestStatus = TripRequestStatus.REQUESTED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
