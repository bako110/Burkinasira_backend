import secrets
from datetime import datetime, timedelta
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
    PublicTicketResponse,
)
from app.schemas.notification import CreateNotificationRequest
from app.schemas.messaging import StartConversationRequest
from app.models.messaging import ConversationKind
from app.services import notification_service
from app.services import messaging_service
from app.services.booking_provider_resolver import resolve_provider_id, resolve_real_price, resolve_guide_hourly_rate

COLLECTION = "bookings"
INVOICES_COLLECTION = "booking_invoices"
USERS_COLLECTION = "users"
CONVERSATIONS_COLLECTION = "conversations"
SLOTS_COLLECTION = "guide_availability_slots"

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
        slot_id=doc.get("slot_id"),
        room_type_name=doc.get("room_type_name"),
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


async def _lock_slot(slot_id: str, guide_id: str) -> dict:
    """Verrouille atomiquement un créneau libre appartenant au guide indiqué.

    Utilise find_one_and_update avec le filtre is_booked=False dans la même
    opération que le verrouillage, pour empêcher deux réservations
    concurrentes de gagner la course sur le même créneau.
    """
    db = get_database()
    if not ObjectId.is_valid(slot_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Créneau introuvable")

    slot = await db[SLOTS_COLLECTION].find_one({"_id": ObjectId(slot_id)})
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Créneau introuvable")
    if slot["guide_id"] != guide_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce créneau n'appartient pas au guide indiqué")

    locked = await db[SLOTS_COLLECTION].find_one_and_update(
        {"_id": ObjectId(slot_id), "is_booked": False},
        {"$set": {"is_booked": True}},
    )
    if not locked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce créneau vient d'être réservé par quelqu'un d'autre")
    return locked


async def _release_slot(slot_id: str) -> None:
    if not slot_id or not ObjectId.is_valid(slot_id):
        return
    db = get_database()
    await db[SLOTS_COLLECTION].update_one({"_id": ObjectId(slot_id)}, {"$set": {"is_booked": False}})


ACTIVE_BOOKING_STATUSES = [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]


def _slot_duration_hours(start_time: str, end_time: str) -> float:
    start_h, start_m = (int(p) for p in start_time.split(":")[:2])
    end_h, end_m = (int(p) for p in end_time.split(":")[:2])
    minutes = (end_h * 60 + end_m) - (start_h * 60 + start_m)
    return max(0, minutes) / 60


INVENTORY_COLLECTION = "hotel_room_inventory"


def _inventory_key(hotel_id: str, room_type_name: str, scheduled_date) -> dict:
    day = scheduled_date.strftime("%Y-%m-%d")
    return {"hotel_id": hotel_id, "room_type_name": room_type_name, "date": day}


async def _reserve_room_inventory(hotel_id: str, room_type_name: str, total_rooms: int, scheduled_date) -> None:
    """Réserve atomiquement une unité de capacité pour (hôtel, type de chambre,
    jour), sans nécessiter de transaction Mongo (le serveur de prod tourne en
    standalone, sans replica set).

    Étape 1 : s'assure que le document d'inventaire existe, en l'initialisant
    à booked_count=0 s'il n'existe pas encore — opération idempotente et sans
    incidence si elle est exécutée plusieurs fois en parallèle (upsert avec
    $setOnInsert uniquement, jamais d'incrément ici).

    Étape 2 : incrémente booked_count dans une opération atomique séparée,
    dont le filtre inclut la condition booked_count < total_rooms — deux
    requêtes concurrentes ne peuvent jamais faire passer le compteur
    au-dessus de total_rooms, car MongoDB sérialise les écritures sur un même
    document.
    """
    db = get_database()
    key = _inventory_key(hotel_id, room_type_name, scheduled_date)

    await db[INVENTORY_COLLECTION].update_one(
        key,
        {"$setOnInsert": {**key, "booked_count": 0}},
        upsert=True,
    )

    result = await db[INVENTORY_COLLECTION].find_one_and_update(
        {**key, "booked_count": {"$lt": total_rooms}},
        {"$inc": {"booked_count": 1}},
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette chambre n'est plus disponible pour cette date",
        )


async def _release_room_inventory(hotel_id: str, room_type_name: str, scheduled_date) -> None:
    db = get_database()
    key = _inventory_key(hotel_id, room_type_name, scheduled_date)
    await db[INVENTORY_COLLECTION].update_one(
        {**key, "booked_count": {"$gt": 0}},
        {"$inc": {"booked_count": -1}},
    )


async def create_booking(data: CreateBookingRequest, customer_id: str) -> BookingResponse:
    db = get_database()
    now = datetime.utcnow()
    reference = _generate_reference()
    provider_id = await resolve_provider_id(data.item_type.value, data.item_id)

    unit_price = data.unit_price
    currency = data.currency
    real_price = await resolve_real_price(data.item_type.value, data.item_id, data.room_type_name)
    if real_price is not None:
        unit_price, currency = real_price

    scheduled_date = data.scheduled_date
    slot_locked = False
    if data.slot_id:
        if data.item_type.value != "guide":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="slot_id n'est utilisable que pour item_type=guide")
        slot = await _lock_slot(data.slot_id, guide_id=data.item_id)
        slot_locked = True
        try:
            scheduled_date = datetime.strptime(f"{slot['date']} {slot['start_time']}", "%Y-%m-%d %H:%M")
            duration_hours = _slot_duration_hours(slot["start_time"], slot["end_time"])
            hourly_rate = await resolve_guide_hourly_rate(data.item_id)
            if hourly_rate is not None:
                unit_price, currency = hourly_rate[0] * duration_hours, hourly_rate[1]
        except Exception:
            await _release_slot(data.slot_id)
            raise

    hotel_room = None
    if data.item_type.value == "hotel" and scheduled_date is not None:
        hotel = await db["hotels"].find_one({"_id": ObjectId(data.item_id)}, {"room_types": 1})
        room_types = hotel.get("room_types", []) if hotel else []
        room_name = data.room_type_name or (room_types[0]["name"] if room_types else None)
        hotel_room = next((r for r in room_types if r["name"] == room_name), None)

    doc = data.model_dump()
    doc["customer_id"] = customer_id
    doc["provider_id"] = provider_id
    doc["booking_reference"] = reference
    doc["unit_price"] = unit_price
    doc["currency"] = currency
    doc["room_type_name"] = hotel_room["name"] if hotel_room else data.room_type_name
    doc["total_price"] = unit_price * data.quantity
    doc["status"] = BookingStatus.PENDING.value
    doc["ticket_qr_code"] = reference
    doc["cancellation_reason"] = None
    doc["scheduled_date"] = scheduled_date
    doc["created_at"] = now
    doc["updated_at"] = now

    room_reserved = False
    if hotel_room:
        await _reserve_room_inventory(data.item_id, hotel_room["name"], hotel_room["total_rooms"], scheduled_date)
        room_reserved = True

    try:
        result = await db[COLLECTION].insert_one(doc)
        inserted_id = result.inserted_id
    except Exception:
        if slot_locked:
            await _release_slot(data.slot_id)
        if room_reserved:
            await _release_room_inventory(data.item_id, hotel_room["name"], scheduled_date)
        raise
    doc["_id"] = inserted_id
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
    return await list_provider_bookings("guide", guide_id, status_filter)


async def list_provider_bookings(item_type: str, item_id: str, status_filter: Optional[BookingStatus] = None) -> list:
    """(Provider) Réservations reçues sur un établissement précis (hôtel, restaurant,
    transport ou guide), avec le nom/téléphone du client."""
    db = get_database()
    query: dict = {"item_type": item_type, "item_id": item_id}
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


async def get_booking_by_reference(reference: str) -> PublicTicketResponse:
    """Utilisé pour présenter/valider un ticket QR Code (route publique, sans
    authentification) — ne doit exposer aucune donnée personnelle du client
    ni du prestataire, ni le prix payé."""
    db = get_database()
    doc = await db[COLLECTION].find_one({"booking_reference": reference})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket introuvable")
    return PublicTicketResponse(
        booking_reference=doc["booking_reference"],
        item_type=doc["item_type"],
        item_title=doc["item_title"],
        quantity=doc["quantity"],
        scheduled_date=doc.get("scheduled_date"),
        status=doc.get("status", BookingStatus.PENDING.value),
    )


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

    result = await db[COLLECTION].update_one(
        {"_id": ObjectId(booking_id), "status": {"$in": list(CANCELLABLE_STATUSES)}},
        {"$set": {"status": BookingStatus.CANCELLED.value, "cancellation_reason": reason, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette réservation ne peut plus être annulée")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(booking_id)})
    booking = _to_response(doc)

    if booking.slot_id:
        await _release_slot(booking.slot_id)

    if booking.item_type.value == "hotel" and booking.room_type_name and booking.scheduled_date:
        await _release_room_inventory(booking.item_id, booking.room_type_name, booking.scheduled_date)

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

    result = await db[COLLECTION].update_one(
        {"_id": ObjectId(booking_id), "status": BookingStatus.CANCELLED.value},
        {"$set": {"status": BookingStatus.REFUNDED.value, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seule une réservation annulée peut être remboursée")
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
