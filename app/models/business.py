from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class BusinessServiceType(str, Enum):
    SALLE_CONFERENCE = "salle_conference"
    SEMINAIRE = "seminaire"
    CONGRES = "congres"
    TEAM_BUILDING = "team_building"
    TRANSPORT_GROUPE = "transport_groupe"
    RESTAURATION_GROUPE = "restauration_groupe"
    PRESTATAIRE_EVENEMENTIEL = "prestataire_evenementiel"
    PHOTOGRAPHIE_AUDIOVISUEL = "photographie_audiovisuel"


class QuoteRequestStatus(str, Enum):
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    QUOTED = "quoted"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class BusinessQuoteRequest(BaseModel):
    """Demande de devis groupé pour un événement professionnel (§29)."""
    id: Optional[str] = Field(default=None, alias="_id")
    requester_id: str
    company_name: str
    service_types: List[BusinessServiceType]
    region: Optional[str] = None
    event_date: Optional[datetime] = None
    participant_count: int = Field(default=1, gt=0)
    notes: Optional[str] = None
    quoted_amount: Optional[float] = None
    currency: str = "XOF"
    status: QuoteRequestStatus = QuoteRequestStatus.SUBMITTED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"


class BusinessInvoice(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    quote_request_id: str
    company_name: str
    amount: float
    currency: str = "XOF"
    status: InvoiceStatus = InvoiceStatus.DRAFT
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class EventParticipant(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    quote_request_id: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
