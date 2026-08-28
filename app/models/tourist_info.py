from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TravelInfoCategory(str, Enum):
    VISA = "visa"
    PASSEPORT = "passeport"
    FORMALITES_ENTREE_SORTIE = "formalites_entree_sortie"
    DOUANES = "douanes"
    PERMIS_TOURISTIQUE = "permis_touristique"
    PERMIS_PHOTO_VIDEO = "permis_photo_video"


class InfoSourceType(str, Enum):
    OFFICIEL = "officiel"
    LIEN_EXTERNE = "lien_externe"
    COMMUNAUTAIRE = "communautaire"


class TravelInfo(BaseModel):
    """Informations administratives et formalités (§15)."""
    id: Optional[str] = Field(default=None, alias="_id")
    category: TravelInfoCategory
    title: str
    content: str
    source_type: InfoSourceType = InfoSourceType.OFFICIEL
    official_url: Optional[str] = None
    country_scope: str = "Burkina Faso"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class DiplomaticContact(BaseModel):
    """Représentations diplomatiques et consulaires."""
    id: Optional[str] = Field(default=None, alias="_id")
    country: str
    type: str = "ambassade"  # "ambassade" ou "consulat"
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
