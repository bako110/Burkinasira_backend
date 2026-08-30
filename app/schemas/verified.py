from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.verified import VerificationDocumentType, VerificationStatus, DisputeStatus, SuspiciousReportType


class SubmitVerificationRequest(BaseModel):
    document_type: VerificationDocumentType
    document_url: str


class ReviewVerificationRequest(BaseModel):
    status: VerificationStatus
    review_notes: Optional[str] = None


class ReviewAccountRequest(BaseModel):
    """(Admin) Approuver ou rejeter le compte pro d'un utilisateur, qu'il ait
    ou non deja soumis un document de verification."""
    approve: bool
    review_notes: Optional[str] = None


class VerificationRequestResponse(BaseModel):
    id: str
    user_id: str
    document_type: VerificationDocumentType
    document_url: str
    status: VerificationStatus
    review_notes: Optional[str] = None
    created_at: datetime


class PendingEstablishmentSummary(BaseModel):
    kind: str  # "hotel" | "restaurant" | "transport" | "artisan"
    name: str


class SubmittedDocumentSummary(BaseModel):
    id: str
    document_type: VerificationDocumentType
    document_url: str
    review_notes: Optional[str] = None
    created_at: datetime


class PendingAccountSummary(BaseModel):
    """(Admin) Compte guide/provider pas encore vérifié, avec les documents et
    établissements en brouillon qu'il a éventuellement déjà soumis. Un compte
    apparaît ici dès sa création (is_verified=False), même sans document
    soumis, pour qu'aucune demande ne reste invisible côté admin."""
    user_id: str
    user_full_name: str
    user_email: str
    user_role: str
    documents: List[SubmittedDocumentSummary] = []
    pending_establishments: List[PendingEstablishmentSummary] = []
    account_created_at: datetime


class CreateDisputeRequest(BaseModel):
    against_user_id: Optional[str] = None
    subject: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=5)
    related_booking_id: Optional[str] = None


class ResolveDisputeRequest(BaseModel):
    status: DisputeStatus
    resolution_notes: Optional[str] = None


class DisputeResponse(BaseModel):
    id: str
    complainant_id: str
    against_user_id: Optional[str] = None
    subject: str
    description: str
    related_booking_id: Optional[str] = None
    status: DisputeStatus
    resolution_notes: Optional[str] = None
    created_at: datetime


class ReportSuspiciousRequest(BaseModel):
    type: SuspiciousReportType
    target_id: str
    reason: str = Field(..., min_length=3)


class SuspiciousReportResponse(BaseModel):
    id: str
    reporter_id: str
    type: SuspiciousReportType
    target_id: str
    reason: str
    status: DisputeStatus
    created_at: datetime
