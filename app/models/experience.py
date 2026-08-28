from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource


class ExperienceType(str, Enum):
    RENCONTRE_HABITANT = "rencontre_habitant"
    VISITE_VILLAGE = "visite_village"
    DECOUVERTE_METIER = "decouverte_metier"
    ATELIER_ARTISANAT = "atelier_artisanat"
    ATELIER_CULINAIRE = "atelier_culinaire"
    AGRITOURISME = "agritourisme"
    BALADE_GUIDEE = "balade_guidee"
    HEBERGEMENT_HABITANT = "hebergement_habitant"
    RENCONTRE_ARTISTE = "rencontre_artiste"
    AUTRE = "autre"


class ExperienceStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class RevenueShare(BaseModel):
    """Répartition transparente des revenus (§5, liée à §39 « Où va mon argent ? »)."""
    host_percent: Optional[float] = None
    community_percent: Optional[float] = None
    platform_percent: Optional[float] = None
    notes: Optional[str] = None


class Experience(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    description: str
    type: ExperienceType
    host_id: str  # référence user (rôle guide ou provider) organisant l'expérience
    host_name: str
    region: str
    city: Optional[str] = None
    location: GeoPoint
    photos: List[str] = []
    duration_minutes: Optional[int] = None
    max_participants: Optional[int] = None
    price_amount: Optional[float] = None
    price_currency: str = "XOF"
    languages: List[str] = []
    revenue_share: Optional[RevenueShare] = None
    average_rating: float = 0.0
    review_count: int = 0
    status: ExperienceStatus = ExperienceStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
