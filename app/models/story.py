from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CultureContentType(str, Enum):
    HISTOIRE = "histoire"
    PATRIMOINE_MATERIEL = "patrimoine_materiel"
    PATRIMOINE_IMMATERIEL = "patrimoine_immateriel"
    TRADITION = "tradition"
    LANGUE = "langue"
    CONTE_LEGENDE = "conte_legende"
    MUSIQUE_DANSE = "musique_danse"
    ARTISANAT = "artisanat"
    COSTUME = "costume"
    GASTRONOMIE = "gastronomie"
    PERSONNALITE = "personnalite"


class CultureMediaType(str, Enum):
    TEXTE = "texte"
    AUDIO = "audio"
    VIDEO = "video"


class CultureContent(BaseModel):
    """Contenu culturel : histoire, patrimoine, contes, guides audio/vidéo (§18)."""
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    type: CultureContentType
    media_type: CultureMediaType = CultureMediaType.TEXTE
    summary: Optional[str] = None
    content: Optional[str] = None  # texte complet si media_type = texte
    media_url: Optional[str] = None  # audio/vidéo
    cover_photo: Optional[str] = None
    region: Optional[str] = None
    related_destination_ids: List[str] = []
    author: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class CulturalRoute(BaseModel):
    """Parcours culturel regroupant plusieurs contenus/lieux à suivre dans l'ordre."""
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    description: Optional[str] = None
    region: Optional[str] = None
    step_destination_ids: List[str] = []
    step_content_ids: List[str] = []
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
