from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class OperatorCategory(str, Enum):
    ETABLISSEMENT_HEBERGEMENT = "etablissement_hebergement"
    RESTAURANT_TOURISME = "restaurant_tourisme"
    GUIDE_PROFESSIONNEL = "guide_professionnel"
    OPERATEUR_VOYAGES = "operateur_voyages"
    ETABLISSEMENT_LOISIRS = "etablissement_loisirs"
    AGENCE_HOTES_HOTESSES = "agence_hotes_hotesses"
    ACTEUR_PATRIMOINE_CULTUREL = "acteur_patrimoine_culturel"
    ARTISTE_ENTREPRENEUR_CULTUREL = "artiste_entrepreneur_culturel"
    ORGANISATEUR_EVENEMENTS = "organisateur_evenements"


class OperatorApplicationStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class OperatorApplication(BaseModel):
    """Dossier de candidature d'un professionnel à une catégorie reconnue (§36)."""
    id: Optional[str] = Field(default=None, alias="_id")
    applicant_id: str
    category: OperatorCategory
    business_name: str
    documents: List[str] = []  # URLs de documents justificatifs
    notes: Optional[str] = None
    status: OperatorApplicationStatus = OperatorApplicationStatus.SUBMITTED
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
