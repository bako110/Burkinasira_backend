from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.booking import BookingItemType, BookingStatus


class CreateBookingRequest(BaseModel):
    item_type: BookingItemType
    item_id: str
    item_title: str
    quantity: int = Field(default=1, gt=0)
    unit_price: float = Field(..., ge=0)
    currency: str = "XOF"
    scheduled_date: Optional[datetime] = None


class BookingResponse(BaseModel):
    id: str
    booking_reference: str
    customer_id: str
    provider_id: Optional[str] = None
    item_type: BookingItemType
    item_id: str
    item_title: str
    quantity: int
    unit_price: float
    total_price: float
    currency: str
    scheduled_date: Optional[datetime] = None
    status: BookingStatus
    ticket_qr_code: str
    cancellation_reason: Optional[str] = None
    created_at: datetime


class GuideBookingResponse(BookingResponse):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None


class CancelBookingRequest(BaseModel):
    reason: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: str
    booking_id: str
    amount: float
    currency: str
    issued_at: datetime
