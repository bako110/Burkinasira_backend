from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MemoryTargetType(str, Enum):
    """Mêmes cibles que les avis (ReviewTargetType) : un souvenir peut être
    laissé sur n'importe quelle fiche détail du site, sans avoir réservé."""
    GUIDE = "guide"
    HOTEL = "hotel"
    RESTAURANT = "restaurant"
    TRANSPORT = "transport"
    DESTINATION = "destination"
    EVENT = "event"
    ARTISAN_PRODUCT = "artisan_product"
    EXPERIENCE = "experience"


class MemoryMediaType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"


class MemoryStatus(str, Enum):
    PUBLISHED = "published"
    FLAGGED = "flagged"
    HIDDEN = "hidden"


class Memory(BaseModel):
    """Souvenir (photo/vidéo) laissé publiquement par un visiteur sur une fiche
    du site — visible par tous, sans condition de réservation préalable
    (contrairement aux avis notés, liés à un booking)."""
    id: Optional[str] = Field(default=None, alias="_id")
    target_type: MemoryTargetType
    target_id: str
    author_id: str
    media_url: str
    media_type: MemoryMediaType
    title: Optional[str] = Field(default=None, max_length=120)
    caption: Optional[str] = Field(default=None, max_length=500)
    status: MemoryStatus = MemoryStatus.PUBLISHED
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
