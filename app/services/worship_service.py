from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.worship import WorshipPlaceType, WorshipPlaceStatus
from app.schemas.worship import (
    CreateWorshipPlaceRequest,
    UpdateWorshipPlaceRequest,
    WorshipPlaceSummary,
    WorshipPlaceDetail,
    WorshipPlaceListResponse,
)

COLLECTION = "worship_places"


def _to_summary(doc: dict) -> WorshipPlaceSummary:
    return WorshipPlaceSummary(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc["type"],
        region=doc["region"],
        city=doc.get("city"),
        location=doc["location"],
    )


def _to_detail(doc: dict) -> WorshipPlaceDetail:
    return WorshipPlaceDetail(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc["type"],
        region=doc["region"],
        city=doc.get("city"),
        location=doc["location"],
        address=doc.get("address"),
        public_events=doc.get("public_events", []),
        visiting_rules=doc.get("visiting_rules"),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_worship_place(data: CreateWorshipPlaceRequest) -> WorshipPlaceDetail:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["status"] = WorshipPlaceStatus.PUBLISHED.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_worship_places(
    type: Optional[WorshipPlaceType] = None,
    region: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> WorshipPlaceListResponse:
    db = get_database()
    query: dict = {"status": WorshipPlaceStatus.PUBLISHED.value}
    if type:
        query["type"] = type.value if isinstance(type, WorshipPlaceType) else type
    if region:
        query["region"] = region

    total = await db[COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    docs = await db[COLLECTION].find(query).skip(skip).limit(page_size).to_list(length=page_size)

    return WorshipPlaceListResponse(
        items=[_to_summary(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_worship_place(place_id: str) -> WorshipPlaceDetail:
    db = get_database()
    if not ObjectId.is_valid(place_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu de culte introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(place_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu de culte introuvable")
    return _to_detail(doc)


async def update_worship_place(place_id: str, data: UpdateWorshipPlaceRequest) -> WorshipPlaceDetail:
    db = get_database()
    if not ObjectId.is_valid(place_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu de culte introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[COLLECTION].update_one({"_id": ObjectId(place_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu de culte introuvable")
    return await get_worship_place(place_id)


async def delete_worship_place(place_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(place_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu de culte introuvable")
    result = await db[COLLECTION].delete_one({"_id": ObjectId(place_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu de culte introuvable")
