import secrets
from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.booking import BookingStatus
from app.models.notification import NotificationCategory
from app.schemas.booking import (
    CreateBookingRequest,
    BookingResponse,
    GuideBookingResponse,
    InvoiceResponse,
)
from app.schemas.notification import CreateNotificationRequest
from app.schemas.messaging import StartConversationRequest
from app.models.messaging import ConversationKind
from app.services import notification_service
from app.services import messaging_service
from app.services.booking_provider_resolver import resolve_provider_id

COLLECTION = "bookings"
INVOICES_COLLECTION = "booking_invoices"
USERS_COLLECTION = "users"
CONVERSATIONS_COLLECTION = "conversations"

CANCELLABLE_STATUSES = {BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value}

_ITEM_TYPE_LABELS = {
    "hotel": "hôtel", "activity": "activité", "guide": "guide", "restaurant": "restaurant",
    "transport": "transport", "event": "événement", "experience": "expérience", "visit": "visite",
}

_CONVERSATION_KIND_BY_ITEM_TYPE = {
    "guide": ConversationKind.TOURISTE_GUIDE,
    "hotel": ConversationKind.TOURISTE_HOTEL,
    "restaurant": ConversationKind.TOURISTE_RESTAURANT,
}


def _generate_reference() -> str:
    year = datetime.utcnow().year
    suffix = secrets.token_hex(3).upper()
    return f"GT-{year}-{suffix}"


def _to_response(doc: dict) -> BookingResponse:
    return BookingResponse(
        id=str(doc["_id"]),
        booking_reference=doc["booking_reference"],
        customer_id=doc["customer_id"],
        provider_id=doc.get("provider_id"),
        item_type=doc["item_type"],
        item_id=doc["item_id"],
        item_title=doc["item_title"],
        quantity=doc["quantity"],
        unit_price=doc["unit_price"],
        total_price=doc["total_price"],
        currency=doc.get("currency", "XOF"),
        scheduled_date=doc.get("scheduled_date"),
        status=doc.get("status", BookingStatus.PENDING.value),
        ticket_qr_code=doc["ticket_qr_code"],
        cancellation_reason=doc.get("cancellation_reason"),
        created_at=doc["created_at"],
    )


async def create_booking(data: CreateBookingRequest, customer_id: str) -> BookingResponse:
    db = get_database()
    now = datetime.utcnow()
    reference = _generate_reference()
    provider_id = await resolve_provider_id(data.item_type.value, data.item_id)

    doc = data.model_dump()
    doc["customer_id"] = customer_id
    doc["provider_id"] = provider_id
    doc["booking_reference"] = reference
    doc["total_price"] = data.unit_price * data.quantity
    doc["status"] = BookingStatus.PENDING.value
    doc["ticket_qr_code"] = reference
    doc["cancellation_reason"] = None
    doc["created_at"] = now
    doc["updated_at"] = now

    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    booking = _to_response(doc)

    if provider_id:
        await notification_service.create_notification(CreateNotificationRequest(
            user_id=provider_id,
            category=NotificationCategory.RESERVATION_CONFIRMATION,
            title="Nouvelle demande de réservation",
            body=f"{data.item_title} : nouvelle réservation en attente de confirmation ({booking.booking_reference}).",
            related_id=booking.id,
        ))

    return booking


async def list_my_bookings(customer_id: str, status_filter: Optional[BookingStatus] = None) -> list:
    db = get_database()
    query: dict = {"customer_id": customer_id}
    if status_filter:
        query["status"] = status_filter.value if isinstance(status_filter, BookingStatus) else status_filter
    docs = await db[COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_to_response(d) for d in docs]


async def list_guide_bookings(guide_id: str, status_filter: Optional[BookingStatus] = None) -> list:
    """(Guide) Réservations reçues sur son propre profil, avec le nom/téléphone du client."""
    db = get_database()
    query: dict = {"item_type": "guide", "item_id": guide_id}
    if status_filter:
        query["status"] = status_filter.value if isinstance(status_filter, BookingStatus) else status_filter
    docs = await db[COLLECTION].find(query).sort("created_at", -1).to_list(length=None)

    customer_ids = {d["customer_id"] for d in docs if ObjectId.is_valid(d["customer_id"])}
    user_docs = await db[USERS_COLLECTION].find({"_id": {"$in": [ObjectId(c) for c in customer_ids]}}).to_list(length=None)
    users_by_id = {str(u["_id"]): u for u in user_docs}

    items = []
    for d in docs:
        customer = users_by_id.get(d["customer_id"])
        items.append(
            GuideBookingResponse(
                **_to_response(d).model_dump(),
                customer_name=customer.get("full_name") if customer else None,
                customer_phone=customer.get("phone") if customer else None,
            )
        )
    return items


async def get_booking(booking_id: str, current_user_id: str, is_admin: bool) -> BookingResponse:
    db = get_database()
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(booking_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    if doc["customer_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à cette réservation")
    return _to_response(doc)


async def get_booking_by_reference(reference: str) -> BookingResponse:
    """Utilisé pour présenter/valider un ticket QR Code."""
    db = get_database()
    doc = await db[COLLECTION].find_one({"booking_reference": reference})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket introuvable")
    return _to_response(doc)


async def confirm_booking(booking_id: str, current_user_id: str, is_admin: bool) -> BookingResponse:
    """(Admin, ou le prestataire propriétaire de l'item) Confirmer une réservation en attente."""
    db = get_database()
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(booking_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    if not is_admin and doc.get("provider_id") != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul le prestataire concerné peut confirmer cette réservation")

    result = await db[COLLECTION].update_one(
        {"_id": ObjectId(booking_id), "status": BookingStatus.PENDING.value},
        {"$set": {"status": BookingStatus.CONFIRMED.value, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Réservation introuvable ou déjà traitée")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(booking_id)})
    booking = _to_response(doc)

    await notification_service.create_notification(CreateNotificationRequest(
        user_id=booking.customer_id,
        category=NotificationCategory.RESERVATION_CONFIRMATION,
        title="Réservation confirmée",
        body=f"Votre réservation {booking.booking_reference} ({booking.item_title}) est confirmée.",
        related_id=booking.id,
    ))

    if booking.provider_id:
        await _ensure_booking_conversation(booking)

    return booking


async def _ensure_booking_conversation(booking: BookingResponse) -> None:
    """Crée (ou relie) la conversation client<->prestataire pour cette réservation."""
    db = get_database()
    existing = await db[CONVERSATIONS_COLLECTION].find_one({"linked_booking_id": booking.id})
    if existing:
        return

    kind = _CONVERSATION_KIND_BY_ITEM_TYPE.get(booking.item_type.value if hasattr(booking.item_type, "value") else booking.item_type)
    if kind is None:
        return

    conversation = await messaging_service.start_conversation(
        StartConversationRequest(
            kind=kind,
            other_user_id=booking.provider_id,
            linked_booking_id=booking.id,
            initial_message=f"Réservation confirmée : {booking.item_title} ({booking.booking_reference}).",
        ),
        initiator_id=booking.customer_id,
    )
    await messaging_service.link_booking(conversation.id, booking.id, booking.customer_id)


async def cancel_booking(booking_id: str, reason: Optional[str], current_user_id: str, is_admin: bool) -> BookingResponse:
    db = get_database()
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(booking_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    if doc["customer_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à cette réservation")
    if doc.get("status") not in CANCELLABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette réservation ne peut plus être annulée")

    await db[COLLECTION].update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": BookingStatus.CANCELLED.value, "cancellation_reason": reason, "updated_at": datetime.utcnow()}},
    )
    doc = await db[COLLECTION].find_one({"_id": ObjectId(booking_id)})
    booking = _to_response(doc)

    notify_user_id = booking.provider_id if current_user_id == booking.customer_id else booking.customer_id
    if notify_user_id:
        await notification_service.create_notification(CreateNotificationRequest(
            user_id=notify_user_id,
            category=NotificationCategory.ANNULATION,
            title="Réservation annulée",
            body=f"La réservation {booking.booking_reference} ({booking.item_title}) a été annulée." + (f" Motif : {reason}" if reason else ""),
            related_id=booking.id,
        ))

    return booking


async def request_refund(booking_id: str, current_user_id: str, is_admin: bool) -> BookingResponse:
    db = get_database()
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(booking_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    if doc["customer_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à cette réservation")
    if doc.get("status") != BookingStatus.CANCELLED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seule une réservation annulée peut être remboursée")

    await db[COLLECTION].update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": BookingStatus.REFUNDED.value, "updated_at": datetime.utcnow()}},
    )
    doc = await db[COLLECTION].find_one({"_id": ObjectId(booking_id)})
    booking = _to_response(doc)

    if booking.provider_id:
        await notification_service.create_notification(CreateNotificationRequest(
            user_id=booking.provider_id,
            category=NotificationCategory.ANNULATION,
            title="Remboursement effectué",
            body=f"La réservation {booking.booking_reference} ({booking.item_title}) a été remboursée.",
            related_id=booking.id,
        ))

    return booking


# --- Factures ---

def _invoice_to_response(doc: dict) -> InvoiceResponse:
    return InvoiceResponse(
        id=str(doc["_id"]),
        booking_id=doc["booking_id"],
        amount=doc["amount"],
        currency=doc.get("currency", "XOF"),
        issued_at=doc["issued_at"],
    )


async def get_or_create_invoice(booking_id: str, current_user_id: str, is_admin: bool) -> InvoiceResponse:
    booking = await get_booking(booking_id, current_user_id, is_admin)
    db = get_database()
    doc = await db[INVOICES_COLLECTION].find_one({"booking_id": booking_id})
    if not doc:
        doc = {
            "booking_id": booking_id,
            "amount": booking.total_price,
            "currency": booking.currency,
            "issued_at": datetime.utcnow(),
        }
        result = await db[INVOICES_COLLECTION].insert_one(doc)
        doc["_id"] = result.inserted_id
    return _invoice_to_response(doc)
