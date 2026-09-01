from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.utils.slug import generate_unique_slug, find_by_slug_or_id, ensure_slug_index
from app.models.connectivity import ConnectivityPointType, ConnectivityPointStatus
from app.schemas.connectivity import (
    CreateConnectivityPointRequest,
    UpdateConnectivityPointRequest,
    ConnectivityPointSummary,
    ConnectivityPointDetail,
    ConnectivityPointListResponse,
)

COLLECTION = "connectivity_points"


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def _to_summary(doc: dict) -> ConnectivityPointSummary:
    return ConnectivityPointSummary(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        type=doc["type"],
        operator=doc.get("operator"),
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        location=doc["location"],
        is_free=doc.get("is_free"),
        offers_esim=doc.get("offers_esim", False),
    )


def _to_detail(doc: dict) -> ConnectivityPointDetail:
    return ConnectivityPointDetail(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        type=doc["type"],
        operator=doc.get("operator"),
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        location=doc["location"],
        address=doc.get("address"),
        is_free=doc.get("is_free"),
        offers_esim=doc.get("offers_esim", False),
        contact_phone=doc.get("contact_phone"),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_point(data: CreateConnectivityPointRequest) -> ConnectivityPointDetail:
    db = get_database()
    await ensure_slug_index(db, COLLECTION)
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["slug"] = await generate_unique_slug(db, COLLECTION, data.name)
    doc["status"] = ConnectivityPointStatus.PUBLISHED.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_points(
    type: Optional[ConnectivityPointType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    page: int = 1,
    page_size: int = 20,
) -> ConnectivityPointListResponse:
    db = get_database()
    query: dict = {"status": ConnectivityPointStatus.PUBLISHED.value}
    if type:
        query["type"] = type.value if isinstance(type, ConnectivityPointType) else type
    if region:
        query["region"] = region
    if province:
        query["province"] = province

    all_docs = await db[COLLECTION].find(query).to_list(length=None)

    if near_lat is not None and near_lng is not None:
        all_docs.sort(
            key=lambda d: _haversine_km(near_lat, near_lng, d["location"]["latitude"], d["location"]["longitude"])
        )
        if radius_km is not None:
            all_docs = [
                d for d in all_docs
                if _haversine_km(near_lat, near_lng, d["location"]["latitude"], d["location"]["longitude"]) <= radius_km
            ]

    total = len(all_docs)
    start = (page - 1) * page_size
    page_docs = all_docs[start:start + page_size]

    return ConnectivityPointListResponse(
        items=[_to_summary(d) for d in page_docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_point(point_id: str) -> ConnectivityPointDetail:
    db = get_database()
    doc = await find_by_slug_or_id(db, COLLECTION, point_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point de connectivité introuvable")
    return _to_detail(doc)


async def update_point(point_id: str, data: UpdateConnectivityPointRequest) -> ConnectivityPointDetail:
    db = get_database()
    if not ObjectId.is_valid(point_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point de connectivité introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[COLLECTION].update_one({"_id": ObjectId(point_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point de connectivité introuvable")
    return await get_point(point_id)


async def delete_point(point_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(point_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point de connectivité introuvable")
    result = await db[COLLECTION].delete_one({"_id": ObjectId(point_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point de connectivité introuvable")
