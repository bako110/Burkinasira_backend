from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ConnectorType(str, Enum):
    CARTOGRAPHIE = "cartographie"
    METEO = "meteo"
    PAIEMENT = "paiement"
    NOTIFICATIONS = "notifications"
    SMS_WHATSAPP = "sms_whatsapp"
    BILLETTERIE = "billetterie"
    HOTELS_RESERVATION = "hotels_reservation"
    DONNEES_PUBLIQUES = "donnees_publiques"


class ConnectorStatus(str, Enum):
    NOT_CONFIGURED = "not_configured"
    CONFIGURED = "configured"
    DISABLED = "disabled"


class IntegrationConnector(BaseModel):
    """Connecteur externe configurable (§46). Les secrets réels vivent en variables
    d'environnement — ce modèle ne stocke que le statut et les métadonnées non sensibles."""
    id: Optional[str] = Field(default=None, alias="_id")
    type: ConnectorType
    provider_name: str  # ex: "Mapbox", "OpenWeather", "Orange Money"
    status: ConnectorStatus = ConnectorStatus.NOT_CONFIGURED
    config_notes: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class WebhookEventType(str, Enum):
    BOOKING_CREATED = "booking_created"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    PAYMENT_CONFIRMED = "payment_confirmed"


class WebhookSubscription(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    owner_id: str
    event_type: WebhookEventType
    target_url: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
