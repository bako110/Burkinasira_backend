from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ImpactInitiativeCategory(str, Enum):
    EXPERIENCE_COMMUNAUTAIRE = "experience_communautaire"
    ARTISAN_PRODUIT_LOCAL = "artisan_produit_local"
    PROJET_ENVIRONNEMENTAL = "projet_environnemental"
    PROJET_EDUCATIF = "projet_educatif"
    PROJET_SANITAIRE = "projet_sanitaire"


class ImpactInitiativeStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ImpactInitiative(BaseModel):
    """Initiative locale mise en avant (§38)."""
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    category: ImpactInitiativeCategory
    description: str
    region: Optional[str] = None
    is_verified: bool = False
    cover_photo: Optional[str] = None
    supporter_count: int = 0
    status: ImpactInitiativeStatus = ImpactInitiativeStatus.PUBLISHED
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class ImpactIndicator(BaseModel):
    """Indicateur d'impact global affiché sur la section (ex: nb familles soutenues)."""
    id: Optional[str] = Field(default=None, alias="_id")
    label: str
    value: float
    unit: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class SupportRecord(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    initiative_id: str
    supporter_id: str
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
