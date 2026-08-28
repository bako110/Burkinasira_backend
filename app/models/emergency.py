from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint


class EmergencyServiceType(str, Enum):
    POLICE = "police"
    POMPIERS = "pompiers"
    GENDARMERIE = "gendarmerie"
    SAMU = "samu"
    AUTRE = "autre"


class EmergencyContact(BaseModel):
    """Numéros officiels administrables (ex. Police 17, Pompiers 18...)."""
    id: Optional[str] = Field(default=None, alias="_id")
    type: EmergencyServiceType
    label: str
    phone_number: str
    region: Optional[str] = None  # None = valable pour tout le pays
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class IncidentStatus(str, Enum):
    REPORTED = "reported"
    REVIEWING = "reviewing"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class IncidentReport(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    reporter_id: Optional[str] = None  # None si signalement anonyme
    title: str
    description: str
    location: Optional[GeoPoint] = None
    status: IncidentStatus = IncidentStatus.REPORTED
    moderated_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class SecurityAlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SecurityAlert(BaseModel):
    """Alertes officielles sur zones/routes à risque."""
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    description: str
    severity: SecurityAlertSeverity = SecurityAlertSeverity.INFO
    region: Optional[str] = None
    location: Optional[GeoPoint] = None
    radius_km: Optional[float] = None
    is_active: bool = True
    published_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class SOSAlert(BaseModel):
    """Déclenchement du bouton SOS par un utilisateur."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    location: GeoPoint
    trusted_contact_phone: Optional[str] = None
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
