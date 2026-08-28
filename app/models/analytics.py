from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AnalyticsEventType(str, Enum):
    SEARCH = "search"
    VIEW = "view"


class AnalyticsEvent(BaseModel):
    """Événement de recherche/consultation, pour le calcul du taux de conversion (§45)."""
    id: Optional[str] = Field(default=None, alias="_id")
    type: AnalyticsEventType
    item_type: Optional[str] = None
    item_id: Optional[str] = None
    query: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
