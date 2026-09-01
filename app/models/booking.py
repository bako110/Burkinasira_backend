from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BookingItemType(str, Enum):
    HOTEL = "hotel"
    ACTIVITY = "activity"
    GUIDE = "guide"
    RESTAURANT = "restaurant"
    TRANSPORT = "transport"
    EVENT = "event"
    EXPERIENCE = "experience"
    VISIT = "visit"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    REFUNDED = "refunded"


class Booking(BaseModel):
    """Réservation générique et billetterie (§33)."""
    id: Optional[str] = Field(default=None, alias="_id")
    booking_reference: str  # code court lisible, ex: "GT-2026-000123"
    customer_id: str
    provider_id: Optional[str] = None  # user_id du prestataire (résolu à la création)
    item_type: BookingItemType
    item_id: str
    slot_id: Optional[str] = None  # créneau de disponibilité verrouillé (item_type == "guide")
    item_title: str
    quantity: int = Field(default=1, gt=0)
    unit_price: float
    total_price: float
    currency: str = "XOF"
    scheduled_date: Optional[datetime] = None
    status: BookingStatus = BookingStatus.PENDING
    ticket_qr_code: str  # payload encodé dans le QR (ex: booking_reference)
    cancellation_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class InvoiceDocument(BaseModel):
    """Facture/reçu numérique associé à une réservation."""
    id: Optional[str] = Field(default=None, alias="_id")
    booking_id: str
    amount: float
    currency: str = "XOF"
    issued_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
