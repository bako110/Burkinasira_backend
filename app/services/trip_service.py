import secrets
from datetime import datetime, date
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.trip import TripStatus
from app.schemas.trip import (
    CreateTripRequest,
    UpdateTripRequest,
    TripSummary,
    TripDetail,
    AddTripDayItemRequest,
    RemoveTripDayItemRequest,
    ShareTripRequest,
)

COLLECTION = "trips"

_token_index_ensured = False


def _dates_to_datetimes(fields: dict) -> None:
    """BSON ne sait pas encoder datetime.date — convertit en datetime à minuit avant insertion/mise à jour."""
    for key in ("start_date", "end_date"):
        value = fields.get(key)
        if isinstance(value, date) and not isinstance(value, datetime):
            fields[key] = datetime.combine(value, datetime.min.time())


async def _ensure_token_index(db) -> None:
    global _token_index_ensured
    if _token_index_ensured:
        return
    await db[COLLECTION].create_index("share_token", unique=True, sparse=True)
    _token_index_ensured = True


async def resolve_trip_id(trip_id_or_token: str) -> str:
    """Accepte soit l'ObjectId réel d'un voyage, soit son token de navigation
    opaque (share_token), et retourne toujours l'ObjectId réel en string.
    Le frontend n'utilise que le token dans ses URLs pour ne pas exposer
    l'identifiant technique du voyage (privé, propre à chaque utilisateur)."""
    if ObjectId.is_valid(trip_id_or_token):
        return trip_id_or_token
    db = get_database()
    doc = await db[COLLECTION].find_one({"share_token": trip_id_or_token}, {"_id": 1})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    return str(doc["_id"])


def _to_summary(doc: dict) -> TripSummary:
    return TripSummary(
        id=doc.get("share_token") or str(doc["_id"]),
        title=doc["title"],
        themes=doc.get("themes", []),
        region=doc.get("region"),
        start_date=doc.get("start_date"),
        end_date=doc.get("end_date"),
        status=doc.get("status", TripStatus.DRAFT.value),
        budget_estimate=doc.get("budget_estimate"),
        currency=doc.get("currency", "XOF"),
    )


def _to_detail(doc: dict) -> TripDetail:
    return TripDetail(
        id=doc.get("share_token") or str(doc["_id"]),
        owner_id=doc["owner_id"],
        title=doc["title"],
        themes=doc.get("themes", []),
        region=doc.get("region"),
        start_date=doc.get("start_date"),
        end_date=doc.get("end_date"),
        budget_estimate=doc.get("budget_estimate"),
        currency=doc.get("currency", "XOF"),
        days=doc.get("days", []),
        linked_booking_ids=doc.get("linked_booking_ids", []),
        collaborators=doc.get("collaborators", []),
        status=doc.get("status", TripStatus.DRAFT.value),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _check_access(doc: dict, user_id: str, require_edit: bool = False) -> None:
    if doc["owner_id"] == user_id:
        return
    for collab in doc.get("collaborators", []):
        if collab["user_id"] == user_id and (not require_edit or collab.get("can_edit")):
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à ce voyage")


async def create_trip(data: CreateTripRequest, owner_id: str) -> TripDetail:
    db = get_database()
    await _ensure_token_index(db)
    now = datetime.utcnow()
    doc = data.model_dump()
    _dates_to_datetimes(doc)
    doc["owner_id"] = owner_id
    doc["days"] = []
    doc["linked_booking_ids"] = []
    doc["collaborators"] = []
    doc["status"] = TripStatus.DRAFT.value
    doc["share_token"] = secrets.token_urlsafe(12)
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_my_trips(user_id: str) -> list:
    db = get_database()
    query = {"$or": [{"owner_id": user_id}, {"collaborators.user_id": user_id}]}
    docs = await db[COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_to_summary(d) for d in docs]


async def get_trip(trip_id: str, user_id: str) -> TripDetail:
    db = get_database()
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(trip_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    _check_access(doc, user_id)
    return _to_detail(doc)


async def update_trip(trip_id: str, data: UpdateTripRequest, user_id: str) -> TripDetail:
    db = get_database()
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(trip_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    _check_access(doc, user_id, require_edit=True)

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        _dates_to_datetimes(update_fields)
        update_fields["updated_at"] = datetime.utcnow()
        await db[COLLECTION].update_one({"_id": ObjectId(trip_id)}, {"$set": update_fields})

    return await get_trip(trip_id, user_id)


async def delete_trip(trip_id: str, user_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(trip_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    if doc["owner_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul le créateur peut supprimer ce voyage")
    await db[COLLECTION].delete_one({"_id": ObjectId(trip_id)})


async def add_day_item(trip_id: str, data: AddTripDayItemRequest, user_id: str) -> TripDetail:
    db = get_database()
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(trip_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    _check_access(doc, user_id, require_edit=True)

    days = doc.get("days", [])
    target_date_str = data.date.isoformat()
    item_dict = data.item.model_dump()
    # BSON ne sait pas encoder datetime.date — on stocke un datetime à minuit
    target_datetime = datetime.combine(data.date, datetime.min.time())

    day_found = False
    for day in days:
        day_date = day["date"]
        day_date_str = day_date.isoformat()[:10] if hasattr(day_date, "isoformat") else str(day_date)[:10]
        if day_date_str == target_date_str:
            day["items"].append(item_dict)
            day_found = True
            break
    if not day_found:
        days.append({"date": target_datetime, "items": [item_dict]})
        days.sort(key=lambda d: d["date"].isoformat() if hasattr(d["date"], "isoformat") else str(d["date"]))

    await db[COLLECTION].update_one(
        {"_id": ObjectId(trip_id)},
        {"$set": {"days": days, "updated_at": datetime.utcnow()}},
    )
    return await get_trip(trip_id, user_id)


async def remove_day_item(trip_id: str, data: RemoveTripDayItemRequest, user_id: str) -> TripDetail:
    db = get_database()
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(trip_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    _check_access(doc, user_id, require_edit=True)

    days = doc.get("days", [])
    target_date_str = data.date.isoformat()
    for day in days:
        day_date = day["date"]
        day_date_str = day_date.isoformat()[:10] if hasattr(day_date, "isoformat") else str(day_date)[:10]
        if day_date_str == target_date_str:
            if 0 <= data.item_index < len(day["items"]):
                day["items"].pop(data.item_index)
            break

    await db[COLLECTION].update_one(
        {"_id": ObjectId(trip_id)},
        {"$set": {"days": days, "updated_at": datetime.utcnow()}},
    )
    return await get_trip(trip_id, user_id)


async def link_booking(trip_id: str, booking_id: str, user_id: str) -> TripDetail:
    db = get_database()
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(trip_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    _check_access(doc, user_id, require_edit=True)

    await db[COLLECTION].update_one(
        {"_id": ObjectId(trip_id)},
        {"$addToSet": {"linked_booking_ids": booking_id}, "$set": {"updated_at": datetime.utcnow()}},
    )
    return await get_trip(trip_id, user_id)


async def share_trip(trip_id: str, data: ShareTripRequest, owner_id: str) -> TripDetail:
    db = get_database()
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(trip_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voyage introuvable")
    if doc["owner_id"] != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul le créateur peut partager ce voyage")

    collaborators = [c for c in doc.get("collaborators", []) if c["user_id"] != data.user_id]
    collaborators.append({"user_id": data.user_id, "can_edit": data.can_edit})

    await db[COLLECTION].update_one(
        {"_id": ObjectId(trip_id)},
        {"$set": {"collaborators": collaborators, "updated_at": datetime.utcnow()}},
    )
    return await get_trip(trip_id, owner_id)
