from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DataErrorReportStatus(str, Enum):
    REPORTED = "reported"
    REVIEWING = "reviewing"
    CORRECTED = "corrected"
    DISMISSED = "dismissed"


class DataErrorReport(BaseModel):
    """Signalement d'une information incorrecte sur une fiche (§44)."""
    id: Optional[str] = Field(default=None, alias="_id")
    reporter_id: str
    item_type: str  # ex: "destination", "hotel", "health_facility"
    item_id: str
    description: str
    status: DataErrorReportStatus = DataErrorReportStatus.REPORTED
    reviewed_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class DataChangeLogEntry(BaseModel):
    """Historique des modifications d'une fiche, pour la traçabilité qualité."""
    id: Optional[str] = Field(default=None, alias="_id")
    item_type: str
    item_id: str
    changed_by: str
    change_summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class DuplicateCandidate(BaseModel):
    """Doublon potentiel détecté entre deux fiches du même type."""
    id: Optional[str] = Field(default=None, alias="_id")
    item_type: str
    item_id_a: str
    item_id_b: str
    similarity_score: float
    resolved: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
