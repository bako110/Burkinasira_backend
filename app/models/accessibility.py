from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint


class AccessibilityFeature(str, Enum):
    ACCES_FAUTEUIL_ROULANT = "acces_fauteuil_roulant"
    RAMPE = "rampe"
    ASCENSEUR = "ascenseur"
    TOILETTES_ACCESSIBLES = "toilettes_accessibles"
    INFO_MALVOYANTS = "info_malvoyants"
    INFO_MALENTENDANTS = "info_malentendants"
    SERVICE_PERSONNES_AGEES = "service_personnes_agees"


class AccessibilityReportStatus(str, Enum):
    REPORTED = "reported"
    REVIEWING = "reviewing"
    CONFIRMED = "confirmed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AccessibilityObstacleReport(BaseModel):
    """Signalement communautaire d'un obstacle d'accessibilité (§23)."""
    id: Optional[str] = Field(default=None, alias="_id")
    reporter_id: str
    location: GeoPoint
    description: str
    related_destination_id: Optional[str] = None
    status: AccessibilityReportStatus = AccessibilityReportStatus.REPORTED
    moderated_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
