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


class VerificationRequestAdminSummary(BaseModel):
    """(Admin) Demande de vérification enrichie avec l'identité du compte et
    un aperçu des établissements en brouillon qu'il a déjà soumis."""
    id: str
    user_id: str
    user_full_name: str
    user_email: str
    user_role: str
    document_type: VerificationDocumentType
    document_url: str
    status: VerificationStatus
    review_notes: Optional[str] = None
    created_at: datetime
    pending_establishments: List[PendingEstablishmentSummary] = []


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
