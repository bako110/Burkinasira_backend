from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class NotificationCategory(str, Enum):
    RESERVATION_CONFIRMATION = "reservation_confirmation"
    RAPPEL_ACTIVITE = "rappel_activite"
    CHANGEMENT_HORAIRE = "changement_horaire"
    ANNULATION = "annulation"
    ALERTE_SECURITE = "alerte_securite"
    ALERTE_METEO = "alerte_meteo"
    EVENEMENT_PROXIMITE = "evenement_proximite"
    PROMOTION_PERSONNALISEE = "promotion_personnalisee"
    MESSAGE_PRESTATAIRE = "message_prestataire"
    RAPPEL_VOYAGE = "rappel_voyage"


class Notification(BaseModel):
    """Notification push/in-app (§41)."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    category: NotificationCategory
    title: str
    body: str
    related_id: Optional[str] = None  # ex: booking_id, alert_id
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class NotificationPreferences(BaseModel):
    """Préférences de notification par catégorie, par utilisateur."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    enabled_categories: List[NotificationCategory] = Field(default_factory=lambda: list(NotificationCategory))
    push_enabled: bool = True
    in_app_enabled: bool = True
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
