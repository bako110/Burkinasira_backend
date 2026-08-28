from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class OfflinePackageType(str, Enum):
    CARTE_REGION = "carte_region"
    GUIDE_CULTUREL = "guide_culturel"
    GUIDE_AUDIO = "guide_audio"
    FICHE_TOURISTIQUE = "fiche_touristique"
    CONTACTS_URGENCE = "contacts_urgence"


class OfflinePackage(BaseModel):
    """Package téléchargeable pour usage hors-ligne (§42)."""
    id: Optional[str] = Field(default=None, alias="_id")
    type: OfflinePackageType
    title: str
    region: Optional[str] = None
    related_destination_id: Optional[str] = None
    file_url: str
    file_size_mb: Optional[float] = None
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class UserDownload(BaseModel):
    """Suivi de ce qu'un utilisateur a téléchargé (pour lister ses contenus hors-ligne)."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    package_id: str
    downloaded_version: int
    downloaded_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
