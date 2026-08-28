from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource


class FamilyServiceType(str, Enum):
    ACTIVITE_FAMILIALE = "activite_familiale"
    SANITAIRE_PUBLIC = "sanitaire_public"
    ESPACE_REPOS = "espace_repos"
    AIRE_JEUX = "aire_jeux"
    GARDE_ENFANTS = "garde_enfants"
    POINT_EAU = "point_eau"


class FamilyServiceStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class FamilyService(BaseModel):
    """Service adapté aux familles et enfants (§22)."""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    type: FamilyServiceType
    description: Optional[str] = None
    region: str
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    is_family_friendly: bool = True
    is_verified_provider: bool = False  # pertinent pour garde d'enfants
    contact_phone: Optional[str] = None
    status: FamilyServiceStatus = FamilyServiceStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
