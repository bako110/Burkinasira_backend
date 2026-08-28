from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FirstVisitGuideCategory(str, Enum):
    CULTURE_USAGES = "culture_usages"
    MONNAIE = "monnaie"
    FORMALITES = "formalites"
    SANTE_SECURITE = "sante_securite"
    TRANSPORT = "transport"


class FirstVisitGuideEntry(BaseModel):
    """Contenu du guide de première visite, multilingue (§32)."""
    id: Optional[str] = Field(default=None, alias="_id")
    category: FirstVisitGuideCategory
    title: str
    content: str
    language: str = "fr"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class SupportedLanguage(BaseModel):
    code: str  # ex: "fr", "en"
    label: str  # ex: "Français", "English"
    is_active: bool = True
