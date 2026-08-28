from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.business import BusinessServiceType, QuoteRequestStatus, InvoiceStatus


class CreateQuoteRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=150)
    service_types: List[BusinessServiceType]
    region: Optional[str] = None
    event_date: Optional[datetime] = None
    participant_count: int = Field(default=1, gt=0)
    notes: Optional[str] = None


class UpdateQuoteRequest(BaseModel):
    status: Optional[QuoteRequestStatus] = None
    quoted_amount: Optional[float] = None
    currency: Optional[str] = None


class QuoteRequestResponse(BaseModel):
    id: str
    requester_id: str
    company_name: str
    service_types: List[BusinessServiceType]
    region: Optional[str] = None
    event_date: Optional[datetime] = None
    participant_count: int
    notes: Optional[str] = None
    quoted_amount: Optional[float] = None
    currency: str
    status: QuoteRequestStatus
    created_at: datetime


class CreateInvoiceRequest(BaseModel):
    quote_request_id: str
    amount: float = Field(..., gt=0)
    currency: str = "XOF"
    due_date: Optional[datetime] = None


class InvoiceResponse(BaseModel):
    id: str
    quote_request_id: str
    company_name: str
    amount: float
    currency: str
    status: InvoiceStatus
    due_date: Optional[datetime] = None
    created_at: datetime


class UpdateInvoiceStatusRequest(BaseModel):
    status: InvoiceStatus


class AddParticipantRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: Optional[str] = None
    phone: Optional[str] = None


class ParticipantResponse(BaseModel):
    id: str
    quote_request_id: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
