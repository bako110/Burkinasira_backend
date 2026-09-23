from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.utils.slug import generate_unique_slug, find_by_slug_or_id, ensure_slug_index
from app.models.health import HealthFacilityType, HealthFacilityStatus
from app.schemas.health import (
    CreateHealthFacilityRequest,
    UpdateHealthFacilityRequest,
    HealthFacilitySummary,
    HealthFacilityDetail,
    HealthFacilityListResponse,
)

COLLECTION = "health_facilities"
FAVORITES_COLLECTION = "health_facility_favorites"


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def _to_summary(doc: dict) -> HealthFacilitySummary:
    return HealthFacilitySummary(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        type=doc["type"],
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        location=doc["location"],
        is_on_duty=doc.get("is_on_duty", False),
        contact_phone=doc.get("contact_phone"),
    )


def _to_detail(doc: dict) -> HealthFacilityDetail:
    return HealthFacilityDetail(
        id=str(doc["_id"]),
        owner_id=doc.get("owner_id"),
        name=doc["name"],
        slug=doc["slug"],
        type=doc["type"],
        description=doc.get("description"),
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        location=doc["location"],
        address=doc.get("address"),
        opening_hours=doc.get("opening_hours", []),
        is_on_duty=doc.get("is_on_duty", False),
        services=doc.get("services", []),
        contact_phone=doc.get("contact_phone"),
        status=doc.get("status", HealthFacilityStatus.PUBLISHED.value),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_health_facility(data: CreateHealthFacilityRequest, owner_id: str, is_admin: bool = False) -> HealthFacilityDetail:
    db = get_database()
    await ensure_slug_index(db, COLLECTION)
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["owner_id"] = owner_id
    doc["slug"] = await generate_unique_slug(db, COLLECTION, data.name)

    if is_admin:
        doc["status"] = HealthFacilityStatus.PUBLISHED.value
    else:
        from app.services import user_service
        owner = await user_service.get_user_by_id(owner_id)
        doc["status"] = HealthFacilityStatus.PUBLISHED.value if owner.is_verified else HealthFacilityStatus.DRAFT.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_at"] = now
    doc["updated_at"] = now

    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_my_health_facilities(owner_id: str) -> list:
    db = get_database()
    from app.services.booking_provider_resolver import list_managed_establishment_ids

    managed_ids = [ObjectId(i) for i in await list_managed_establishment_ids(owner_id, "health") if ObjectId.is_valid(i)]
    query = {"$or": [{"owner_id": owner_id}, {"_id": {"$in": managed_ids}}]} if managed_ids else {"owner_id": owner_id}
    docs = await db[COLLECTION].find(query).to_list(length=None)
    return [_to_detail(d) for d in docs]


async def list_health_facilities(
    type: Optional[HealthFacilityType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    on_duty_only: bool = False,
    q: Optional[str] = None,
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    page: int = 1,
    page_size: int = 20,
) -> HealthFacilityListResponse:
    db = get_database()
    query: dict = {"status": HealthFacilityStatus.PUBLISHED.value}

    if type:
        query["type"] = type.value if isinstance(type, HealthFacilityType) else type
    if region:
        query["region"] = region
    if province:
        query["province"] = province
    if on_duty_only:
        query["is_on_duty"] = True
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"city": {"$regex": q, "$options": "i"}},
            {"address": {"$regex": q, "$options": "i"}},
        ]

    all_docs = await db[COLLECTION].find(query).to_list(length=None)

    if near_lat is not None and near_lng is not None and radius_km is not None:
        all_docs = [
            d for d in all_docs
            if _haversine_km(near_lat, near_lng, d["location"]["latitude"], d["location"]["longitude"]) <= radius_km
        ]

    total = len(all_docs)
    start = (page - 1) * page_size
    page_docs = all_docs[start:start + page_size]

    return HealthFacilityListResponse(
        items=[_to_summary(d) for d in page_docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_health_facility(facility_id: str) -> HealthFacilityDetail:
    db = get_database()
    doc = await find_by_slug_or_id(db, COLLECTION, facility_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Établissement de santé introuvable")
    return _to_detail(doc)


async def update_health_facility(
    facility_id: str, data: UpdateHealthFacilityRequest, current_user_id: str, is_admin: bool
) -> HealthFacilityDetail:
    db = get_database()
    if not ObjectId.is_valid(facility_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Établissement de santé introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(facility_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Établissement de santé introuvable")
    if not is_admin:
        from app.services.booking_provider_resolver import is_authorized_for_establishment

        if not await is_authorized_for_establishment("health", facility_id, current_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez modifier que vos propres établissements")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        update_fields["data_source.last_updated_at"] = datetime.utcnow()
        await db[COLLECTION].update_one({"_id": ObjectId(facility_id)}, {"$set": update_fields})

    return await get_health_facility(facility_id)


async def delete_health_facility(facility_id: str, current_user_id: str, is_admin: bool) -> None:
    db = get_database()
    if not ObjectId.is_valid(facility_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Établissement de santé introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(facility_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Établissement de santé introuvable")
    if doc.get("owner_id") != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres établissements")
    await db[COLLECTION].delete_one({"_id": ObjectId(facility_id)})


async def add_favorite(user_id: str, facility_id: str) -> None:
    db = get_database()
    await get_health_facility(facility_id)  # 404 si inexistant
    await db[FAVORITES_COLLECTION].update_one(
        {"user_id": user_id, "facility_id": facility_id},
        {"$set": {"user_id": user_id, "facility_id": facility_id, "created_at": datetime.utcnow()}},
        upsert=True,
    )


async def remove_favorite(user_id: str, facility_id: str) -> None:
    db = get_database()
    await db[FAVORITES_COLLECTION].delete_one({"user_id": user_id, "facility_id": facility_id})


async def list_favorites(user_id: str) -> list:
    db = get_database()
    fav_docs = await db[FAVORITES_COLLECTION].find({"user_id": user_id}).to_list(length=None)
    facility_ids = [ObjectId(f["facility_id"]) for f in fav_docs if ObjectId.is_valid(f["facility_id"])]
    if not facility_ids:
        return []
    docs = await db[COLLECTION].find({"_id": {"$in": facility_ids}}).to_list(length=None)
    return [_to_summary(d) for d in docs]
