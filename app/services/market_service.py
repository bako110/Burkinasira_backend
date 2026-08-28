from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.market import MarketPlaceType, MarketPlaceStatus
from app.schemas.market import (
    CreateMarketPlaceRequest,
    UpdateMarketPlaceRequest,
    MarketPlaceSummary,
    MarketPlaceDetail,
    MarketPlaceListResponse,
)

COLLECTION = "marketplaces"


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def _has_active_promo(doc: dict) -> bool:
    now = datetime.utcnow()
    for promo in doc.get("promotions", []):
        valid_from = promo.get("valid_from")
        valid_until = promo.get("valid_until")
        if (valid_from is None or valid_from <= now) and (valid_until is None or valid_until >= now):
            return True
    return False


def _to_summary(doc: dict) -> MarketPlaceSummary:
    return MarketPlaceSummary(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc["type"],
        region=doc["region"],
        city=doc.get("city"),
        location=doc["location"],
        has_active_promotion=_has_active_promo(doc),
    )


def _to_detail(doc: dict) -> MarketPlaceDetail:
    return MarketPlaceDetail(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc["type"],
        description=doc.get("description"),
        products_sold=doc.get("products_sold", []),
        region=doc["region"],
        city=doc.get("city"),
        location=doc["location"],
        address=doc.get("address"),
        opening_hours=doc.get("opening_hours", []),
        promotions=doc.get("promotions", []),
        contact_phone=doc.get("contact_phone"),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_marketplace(data: CreateMarketPlaceRequest) -> MarketPlaceDetail:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["promotions"] = []
    doc["status"] = MarketPlaceStatus.PUBLISHED.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_marketplaces(
    type: Optional[MarketPlaceType] = None,
    region: Optional[str] = None,
    product: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> MarketPlaceListResponse:
    db = get_database()
    query: dict = {"status": MarketPlaceStatus.PUBLISHED.value}
    if type:
        query["type"] = type.value if isinstance(type, MarketPlaceType) else type
    if region:
        query["region"] = region
    if product:
        query["products_sold"] = {"$regex": product, "$options": "i"}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]

    total = await db[COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    docs = await db[COLLECTION].find(query).skip(skip).limit(page_size).to_list(length=page_size)

    return MarketPlaceListResponse(
        items=[_to_summary(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_marketplace(marketplace_id: str) -> MarketPlaceDetail:
    db = get_database()
    if not ObjectId.is_valid(marketplace_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marché/commerce introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(marketplace_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marché/commerce introuvable")
    return _to_detail(doc)


async def update_marketplace(marketplace_id: str, data: UpdateMarketPlaceRequest) -> MarketPlaceDetail:
    db = get_database()
    if not ObjectId.is_valid(marketplace_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marché/commerce introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[COLLECTION].update_one({"_id": ObjectId(marketplace_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marché/commerce introuvable")
    return await get_marketplace(marketplace_id)


async def delete_marketplace(marketplace_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(marketplace_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marché/commerce introuvable")
    result = await db[COLLECTION].delete_one({"_id": ObjectId(marketplace_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marché/commerce introuvable")
