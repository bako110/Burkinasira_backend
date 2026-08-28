from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource, OpeningHours


class MarketPlaceType(str, Enum):
    MARCHE = "marche"
    SUPERMARCHE = "supermarche"
    BOUTIQUE_SPECIALISEE = "boutique_specialisee"
    COMMERCE_LOCAL = "commerce_local"


class MarketPlaceStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Promotion(BaseModel):
    title: str
    description: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class MarketPlace(BaseModel):
    """Marché, supermarché ou boutique spécialisée référencé (§20)."""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    type: MarketPlaceType
    description: Optional[str] = None
    products_sold: List[str] = []  # ex: "légumes", "textile", "produits locaux"
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours] = []
    promotions: List[Promotion] = []
    contact_phone: Optional[str] = None
    status: MarketPlaceStatus = MarketPlaceStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
