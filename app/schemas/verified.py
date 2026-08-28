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
