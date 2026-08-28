from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.schemas.guide import AvailabilitySlotRequest, AvailabilitySlotResponse

COLLECTION = "guide_availability_slots"


def _to_response(doc: dict) -> AvailabilitySlotResponse:
    return AvailabilitySlotResponse(
        id=str(doc["_id"]),
        guide_id=doc["guide_id"],
        date=doc["date"],
        start_time=doc["start_time"],
        end_time=doc["end_time"],
        is_booked=doc.get("is_booked", False),
    )


async def add_slot(guide_id: str, data: AvailabilitySlotRequest) -> AvailabilitySlotResponse:
    db = get_database()
    doc = {
        "guide_id": guide_id,
        "date": data.date,
        "start_time": data.start_time,
        "end_time": data.end_time,
        "is_booked": False,
    }
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_response(doc)


async def list_slots(guide_id: str, date: str = None, available_only: bool = False) -> list:
    db = get_database()
    query: dict = {"guide_id": guide_id}
    if date:
        query["date"] = date
    if available_only:
        query["is_booked"] = False

    docs = await db[COLLECTION].find(query).sort([("date", 1), ("start_time", 1)]).to_list(length=None)
    return [_to_response(d) for d in docs]


async def delete_slot(slot_id: str, guide_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(slot_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Créneau introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(slot_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Créneau introuvable")
    if doc["guide_id"] != guide_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres créneaux")
    if doc.get("is_booked"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce créneau est déjà réservé")
    await db[COLLECTION].delete_one({"_id": ObjectId(slot_id)})


async def mark_slot_booked(slot_id: str) -> AvailabilitySlotResponse:
    db = get_database()
    if not ObjectId.is_valid(slot_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Créneau introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(slot_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Créneau introuvable")
    if doc.get("is_booked"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce créneau est déjà réservé")
    await db[COLLECTION].update_one({"_id": ObjectId(slot_id)}, {"$set": {"is_booked": True}})
    doc["is_booked"] = True
    return _to_response(doc)
