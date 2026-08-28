from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.edu import EduOutingType, EduOutingStatus, EduBookingStatus
from app.schemas.edu import (
    CreateOutingRequest,
    UpdateOutingRequest,
    OutingResponse,
    CreateEduBookingRequest,
    EduBookingResponse,
    AddEduParticipantRequest,
    EduParticipantResponse,
)

OUTINGS_COLLECTION = "edu_outings"
BOOKINGS_COLLECTION = "edu_bookings"
PARTICIPANTS_COLLECTION = "edu_participants"


# --- Sorties éducatives ---

def _outing_to_response(doc: dict) -> OutingResponse:
    return OutingResponse(
        id=str(doc["_id"]),
        organizer_id=doc["organizer_id"],
        title=doc["title"],
        type=doc["type"],
        description=doc["description"],
        region=doc["region"],
        city=doc.get("city"),
        location=doc.get("location"),
        target_level=doc.get("target_level"),
        price_per_participant=doc.get("price_per_participant"),
        currency=doc.get("currency", "XOF"),
        max_participants=doc.get("max_participants"),
        created_at=doc["created_at"],
    )


async def create_outing(data: CreateOutingRequest, organizer_id: str) -> OutingResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["organizer_id"] = organizer_id
    doc["status"] = EduOutingStatus.PUBLISHED.value
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[OUTINGS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _outing_to_response(doc)


async def list_outings(
    type: Optional[EduOutingType] = None,
    region: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    db = get_database()
    query: dict = {"status": EduOutingStatus.PUBLISHED.value}
    if type:
        query["type"] = type.value if isinstance(type, EduOutingType) else type
    if region:
        query["region"] = region

    total = await db[OUTINGS_COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    docs = await db[OUTINGS_COLLECTION].find(query).skip(skip).limit(page_size).to_list(length=page_size)
    return {"items": [_outing_to_response(d) for d in docs], "total": total, "page": page, "page_size": page_size}


async def get_outing(outing_id: str) -> OutingResponse:
    db = get_database()
    if not ObjectId.is_valid(outing_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sortie éducative introuvable")
    doc = await db[OUTINGS_COLLECTION].find_one({"_id": ObjectId(outing_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sortie éducative introuvable")
    return _outing_to_response(doc)


async def update_outing(outing_id: str, data: UpdateOutingRequest, current_user_id: str, is_admin: bool) -> OutingResponse:
    db = get_database()
    if not ObjectId.is_valid(outing_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sortie éducative introuvable")
    doc = await db[OUTINGS_COLLECTION].find_one({"_id": ObjectId(outing_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sortie éducative introuvable")
    if doc["organizer_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez modifier que vos propres sorties")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[OUTINGS_COLLECTION].update_one({"_id": ObjectId(outing_id)}, {"$set": update_fields})

    return await get_outing(outing_id)


async def delete_outing(outing_id: str, current_user_id: str, is_admin: bool) -> None:
    db = get_database()
    if not ObjectId.is_valid(outing_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sortie éducative introuvable")
    doc = await db[OUTINGS_COLLECTION].find_one({"_id": ObjectId(outing_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sortie éducative introuvable")
    if doc["organizer_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres sorties")
    await db[OUTINGS_COLLECTION].delete_one({"_id": ObjectId(outing_id)})


# --- Réservations ---

def _booking_to_response(doc: dict) -> EduBookingResponse:
    return EduBookingResponse(
        id=str(doc["_id"]),
        outing_id=doc["outing_id"],
        booked_by=doc["booked_by"],
        group_name=doc["group_name"],
        participant_count=doc["participant_count"],
        status=doc.get("status", EduBookingStatus.REQUESTED.value),
        created_at=doc["created_at"],
    )


async def book_outing(data: CreateEduBookingRequest, booked_by: str) -> EduBookingResponse:
    await get_outing(data.outing_id)  # 404 si inexistant

    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["booked_by"] = booked_by
    doc["status"] = EduBookingStatus.REQUESTED.value
    doc["created_at"] = now
    result = await db[BOOKINGS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _booking_to_response(doc)


async def list_my_bookings(booked_by: str) -> list:
    db = get_database()
    docs = await db[BOOKINGS_COLLECTION].find({"booked_by": booked_by}).sort("created_at", -1).to_list(length=None)
    return [_booking_to_response(d) for d in docs]


# --- Participants ---

def _participant_to_response(doc: dict) -> EduParticipantResponse:
    return EduParticipantResponse(
        id=str(doc["_id"]),
        booking_id=doc["booking_id"],
        full_name=doc["full_name"],
        notes=doc.get("notes"),
    )


async def add_participant(booking_id: str, data: AddEduParticipantRequest, current_user_id: str) -> EduParticipantResponse:
    db = get_database()
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    booking = await db[BOOKINGS_COLLECTION].find_one({"_id": ObjectId(booking_id)})
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    if booking["booked_by"] != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez gérer que vos propres groupes")

    doc = data.model_dump()
    doc["booking_id"] = booking_id
    doc["created_at"] = datetime.utcnow()
    result = await db[PARTICIPANTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _participant_to_response(doc)


async def list_participants(booking_id: str) -> list:
    db = get_database()
    docs = await db[PARTICIPANTS_COLLECTION].find({"booking_id": booking_id}).to_list(length=None)
    return [_participant_to_response(d) for d in docs]
