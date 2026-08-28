from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ConsentType(str, Enum):
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    LOCATION_TRACKING = "location_tracking"
    PERSONALIZED_RECOMMENDATIONS = "personalized_recommendations"


class UserConsent(BaseModel):
    """Consentement RGPD-like par catégorie de données (§47)."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    consent_type: ConsentType
    granted: bool
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class SensitiveActionType(str, Enum):
    DATA_EXPORT_REQUESTED = "data_export_requested"
    ACCOUNT_DELETION_REQUESTED = "account_deletion_requested"
    CONSENT_UPDATED = "consent_updated"
    LOCATION_ACCESS_CHANGED = "location_access_changed"


class PrivacyActionLog(BaseModel):
    """Journalisation des actions sensibles liées à la vie privée (§47)."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    action: SensitiveActionType
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class DataRetentionPolicy(BaseModel):
    """Politique de conservation des données, par type."""
    id: Optional[str] = Field(default=None, alias="_id")
    data_category: str  # ex: "booking_history", "location_logs"
    retention_days: int
    description: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
