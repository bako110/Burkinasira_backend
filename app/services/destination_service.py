import re
from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from typing import Optional, List
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.destination import DestinationCategory, DestinationStatus
from app.schemas.destination import (
    CreateDestinationRequest,
    UpdateDestinationRequest,
    DestinationSummary,
    DestinationDetail,
    DestinationListResponse,
)

COLLECTION = "destinations"


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def _to_summary(doc: dict) -> DestinationSummary:
    return DestinationSummary(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        category=doc["category"],
        region=doc["region"],
        city=doc.get("city"),
        location=doc["location"],
        photo=doc["photos"][0] if doc.get("photos") else None,
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        price_info=doc.get("price_info"),
    )


def _to_detail(doc: dict) -> DestinationDetail:
    return DestinationDetail(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        description=doc["description"],
        category=doc["category"],
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        location=doc["location"],
        address=doc.get("address"),
        photos=doc.get("photos", []),
        videos=doc.get("videos", []),
        opening_hours=doc.get("opening_hours", []),
        price_info=doc.get("price_info"),
        contact_phone=doc.get("contact_phone"),
        contact_email=doc.get("contact_email"),
        booking_url=doc.get("booking_url"),
        services_on_site=doc.get("services_on_site", []),
        accessibility=doc.get("accessibility", {}),
        history=doc.get("history"),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_destination(data: CreateDestinationRequest, created_by: str) -> DestinationDetail:
    db = get_database()
    now = datetime.utcnow()
    slug = _slugify(data.name)

    doc = data.model_dump()
    doc["slug"] = slug
    doc["average_rating"] = 0.0
    doc["review_count"] = 0
    doc["status"] = DestinationStatus.PUBLISHED.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_by"] = created_by
    doc["created_at"] = now
    doc["updated_at"] = now

    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_destinations(
    category: Optional[DestinationCategory] = None,
    region: Optional[str] = None,
    q: Optional[str] = None,
    min_rating: Optional[float] = None,
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    page: int = 1,
    page_size: int = 20,
) -> DestinationListResponse:
    db = get_database()
    query: dict = {"status": DestinationStatus.PUBLISHED.value}

    if category:
        query["category"] = category.value if isinstance(category, DestinationCategory) else category
    if region:
        query["region"] = region
    if min_rating is not None:
        query["average_rating"] = {"$gte": min_rating}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"city": {"$regex": q, "$options": "i"}},
        ]

    cursor = db[COLLECTION].find(query)
    all_docs = await cursor.to_list(length=None)

    if near_lat is not None and near_lng is not None and radius_km is not None:
        all_docs = [
            d for d in all_docs
            if _haversine_km(near_lat, near_lng, d["location"]["latitude"], d["location"]["longitude"]) <= radius_km
        ]

    total = len(all_docs)
    start = (page - 1) * page_size
    page_docs = all_docs[start:start + page_size]

    return DestinationListResponse(
        items=[_to_summary(d) for d in page_docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_destination(destination_id: str) -> DestinationDetail:
    db = get_database()
    if not ObjectId.is_valid(destination_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(destination_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu introuvable")
    return _to_detail(doc)


async def get_destination_by_slug(slug: str) -> DestinationDetail:
    db = get_database()
    doc = await db[COLLECTION].find_one({"slug": slug})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu introuvable")
    return _to_detail(doc)


async def update_destination(destination_id: str, data: UpdateDestinationRequest) -> DestinationDetail:
    db = get_database()
    if not ObjectId.is_valid(destination_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu introuvable")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[COLLECTION].update_one(
            {"_id": ObjectId(destination_id)}, {"$set": update_fields}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu introuvable")

    return await get_destination(destination_id)


async def delete_destination(destination_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(destination_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu introuvable")
    result = await db[COLLECTION].delete_one({"_id": ObjectId(destination_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieu introuvable")


async def get_nearby_destinations(
    destination_id: str, radius_km: float = 5.0, limit: int = 10
) -> List[DestinationSummary]:
    current = await get_destination(destination_id)
    db = get_database()
    query = {
        "status": DestinationStatus.PUBLISHED.value,
        "_id": {"$ne": ObjectId(destination_id)},
    }
    all_docs = await db[COLLECTION].find(query).to_list(length=None)
    nearby = [
        d for d in all_docs
        if _haversine_km(
            current.location.latitude, current.location.longitude,
            d["location"]["latitude"], d["location"]["longitude"],
        ) <= radius_km
    ]
    nearby.sort(
        key=lambda d: _haversine_km(
            current.location.latitude, current.location.longitude,
            d["location"]["latitude"], d["location"]["longitude"],
        )
    )
    return [_to_summary(d) for d in nearby[:limit]]
