from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.event import EventCategory, EventStatus
from app.schemas.event import (
    CreateEventRequest,
    UpdateEventRequest,
    EventSummary,
    EventDetail,
    EventListResponse,
)

COLLECTION = "events"


def _to_summary(doc: dict) -> EventSummary:
    return EventSummary(
        id=str(doc["_id"]),
        title=doc["title"],
        category=doc["category"],
        region=doc["region"],
        city=doc.get("city"),
        photo=doc["photos"][0] if doc.get("photos") else None,
        start_date=doc["start_date"],
        end_date=doc.get("end_date"),
        ticket_price=doc.get("ticket_price"),
        currency=doc.get("currency", "XOF"),
        requires_ticket=doc.get("requires_ticket", False),
    )


def _to_detail(doc: dict) -> EventDetail:
    return EventDetail(
        id=str(doc["_id"]),
        organizer_id=doc["organizer_id"],
        title=doc["title"],
        description=doc["description"],
        category=doc["category"],
        region=doc["region"],
        city=doc.get("city"),
        location=doc["location"],
        address=doc.get("address"),
        photos=doc.get("photos", []),
        start_date=doc["start_date"],
        end_date=doc.get("end_date"),
        program=doc.get("program", []),
        ticket_price=doc.get("ticket_price"),
        currency=doc.get("currency", "XOF"),
        requires_ticket=doc.get("requires_ticket", False),
        linked_hotel_ids=doc.get("linked_hotel_ids", []),
        linked_transport_provider_ids=doc.get("linked_transport_provider_ids", []),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_event(data: CreateEventRequest, organizer_id: str) -> EventDetail:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["organizer_id"] = organizer_id
    doc["status"] = EventStatus.PUBLISHED.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_events(
    category: Optional[EventCategory] = None,
    region: Optional[str] = None,
    upcoming_only: bool = True,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> EventListResponse:
    db = get_database()
    query: dict = {"status": EventStatus.PUBLISHED.value}
    if category:
        query["category"] = category.value if isinstance(category, EventCategory) else category
    if region:
        query["region"] = region
    if upcoming_only:
        query["start_date"] = {"$gte": datetime.utcnow()}
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]

    total = await db[COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    cursor = db[COLLECTION].find(query).sort("start_date", 1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    return EventListResponse(
        items=[_to_summary(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_event(event_id: str) -> EventDetail:
    db = get_database()
    if not ObjectId.is_valid(event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(event_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    return _to_detail(doc)


async def update_event(event_id: str, data: UpdateEventRequest, current_user_id: str, is_admin: bool) -> EventDetail:
    db = get_database()
    if not ObjectId.is_valid(event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(event_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    if doc["organizer_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez modifier que vos propres événements")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[COLLECTION].update_one({"_id": ObjectId(event_id)}, {"$set": update_fields})

    return await get_event(event_id)


async def delete_event(event_id: str, current_user_id: str, is_admin: bool) -> None:
    db = get_database()
    if not ObjectId.is_valid(event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(event_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    if doc["organizer_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres événements")
    await db[COLLECTION].delete_one({"_id": ObjectId(event_id)})
