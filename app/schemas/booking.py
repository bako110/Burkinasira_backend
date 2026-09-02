from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.models.booking import BookingItemType, BookingStatus


class CreateBookingRequest(BaseModel):
    item_type: BookingItemType
    item_id: str
    item_title: str
    quantity: int = Field(default=1, gt=0, le=20)
    unit_price: float = Field(
        default=0,
        ge=0,
        description="Indicatif seulement : le serveur recalcule le prix réel pour "
        "les types d'item qui ont une source de prix fiable (hotel, event, guide).",
    )
    currency: str = "XOF"
    scheduled_date: Optional[datetime] = None
    room_type_name: Optional[str] = Field(
        default=None, description="Type de chambre choisi (item_type == \"hotel\")."
    )
    slot_id: Optional[str] = Field(
        default=None,
        description="Créneau de disponibilité choisi (item_type == \"guide\"). "
        "Verrouille le créneau et déduit scheduled_date automatiquement.",
    )

    @field_validator("scheduled_date")
    @classmethod
    def reject_past_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v
        now = datetime.now(timezone.utc) if v.tzinfo is not None else datetime.utcnow()
        if v < now:
            raise ValueError("La date de réservation ne peut pas être dans le passé")
        return v


class BookingResponse(BaseModel):
    id: str
    booking_reference: str
    customer_id: str
    provider_id: Optional[str] = None
    item_type: BookingItemType
    item_id: str
    slot_id: Optional[str] = None
    room_type_name: Optional[str] = None
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


class PublicTicketResponse(BaseModel):
    """Vue restreinte d'une réservation pour la validation d'un ticket QR
    (route publique) — n'expose ni customer_id, ni provider_id, ni prix."""
    booking_reference: str
    item_type: BookingItemType
    item_title: str
    quantity: int
    scheduled_date: Optional[datetime] = None
    status: BookingStatus


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
