from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class VerificationDocumentType(str, Enum):
    PIECE_IDENTITE = "piece_identite"
    DOCUMENT_PROFESSIONNEL = "document_professionnel"
    JUSTIFICATIF_ADRESSE = "justificatif_adresse"
    AUTRE = "autre"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class VerificationRequest(BaseModel):
    """Demande de vérification d'identité/documents (§37)."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    document_type: VerificationDocumentType
    document_url: str
    status: VerificationStatus = VerificationStatus.PENDING
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class DisputeStatus(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class Dispute(BaseModel):
    """Litige ouvert au centre de résolution."""
    id: Optional[str] = Field(default=None, alias="_id")
    complainant_id: str
    against_user_id: Optional[str] = None
    subject: str
    description: str
    related_booking_id: Optional[str] = None
    status: DisputeStatus = DisputeStatus.OPEN
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class SuspiciousReportType(str, Enum):
    PROFIL_SUSPECT = "profil_suspect"
    CONTENU_SUSPECT = "contenu_suspect"


class SuspiciousActivityReport(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    reporter_id: str
    type: SuspiciousReportType
    target_id: str  # user_id ou content_id selon le type
    reason: str
    status: DisputeStatus = DisputeStatus.OPEN
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
