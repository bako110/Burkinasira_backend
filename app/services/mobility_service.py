from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.utils.slug import generate_unique_slug, find_by_slug_or_id, ensure_slug_index
from app.utils.geo import filter_and_sort_by_distance
from app.models.mobility import TransportType, TransportProviderStatus, TripRequestStatus
from app.schemas.mobility import (
    CreateTransportProviderRequest,
    UpdateTransportProviderRequest,
    TransportProviderSummary,
    TransportProviderDetail,
    TransportProviderListResponse,
    CreateTripRequest,
    TripRequestResponse,
)

PROVIDERS_COLLECTION = "transport_providers"
TRIPS_COLLECTION = "trip_requests"


def _provider_to_summary(doc: dict) -> TransportProviderSummary:
    return TransportProviderSummary(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        type=doc["type"],
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        photo=doc["photos"][0] if doc.get("photos") else None,
        price_estimate=doc.get("price_estimate"),
        price_currency=doc.get("price_currency", "XOF"),
        is_verified=doc.get("is_verified", False),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
    )


def _provider_to_detail(doc: dict) -> TransportProviderDetail:
    return TransportProviderDetail(
        id=str(doc["_id"]),
        owner_id=doc["owner_id"],
        name=doc["name"],
        slug=doc["slug"],
        type=doc["type"],
        description=doc.get("description"),
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        base_location=doc.get("base_location"),
        vehicle_info=doc.get("vehicle_info"),
        photos=doc.get("photos", []),
        videos=doc.get("videos", []),
        price_estimate=doc.get("price_estimate"),
        price_currency=doc.get("price_currency", "XOF"),
        contact_phone=doc["contact_phone"],
        is_verified=doc.get("is_verified", False),
        status=doc.get("status", TransportProviderStatus.PENDING.value),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_provider(data: CreateTransportProviderRequest, owner_id: str) -> TransportProviderDetail:
    db = get_database()
    await ensure_slug_index(db, PROVIDERS_COLLECTION)
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["owner_id"] = owner_id
    doc["slug"] = await generate_unique_slug(db, PROVIDERS_COLLECTION, data.name)
    doc["is_verified"] = False
    doc["status"] = TransportProviderStatus.PENDING.value
    doc["average_rating"] = 0.0
    doc["review_count"] = 0
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[PROVIDERS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _provider_to_detail(doc)


async def list_providers(
    type: Optional[TransportType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    include_all_statuses: bool = False,
    q: Optional[str] = None,
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    page: int = 1,
    page_size: int = 20,
) -> TransportProviderListResponse:
    db = get_database()
    query: dict = {} if include_all_statuses else {"status": TransportProviderStatus.ACTIVE.value}
    if type:
        query["type"] = type.value if isinstance(type, TransportType) else type
    if region:
        query["region"] = region
    if province:
        query["province"] = province
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"city": {"$regex": q, "$options": "i"}},
            {"vehicle_info": {"$regex": q, "$options": "i"}},
        ]

    if near_lat is not None and near_lng is not None:
        all_docs = await db[PROVIDERS_COLLECTION].find(query).to_list(length=None)
        # Un transporteur est localisé par sa base d'exploitation (base_location).
        all_docs = filter_and_sort_by_distance(all_docs, near_lat, near_lng, radius_km, "base_location")
        total = len(all_docs)
        start = (page - 1) * page_size
        docs = all_docs[start:start + page_size]
    else:
        total = await db[PROVIDERS_COLLECTION].count_documents(query)
        skip = (page - 1) * page_size
        docs = await db[PROVIDERS_COLLECTION].find(query).skip(skip).limit(page_size).to_list(length=page_size)

    return TransportProviderListResponse(
        items=[_provider_to_summary(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def list_my_providers(owner_id: str) -> list:
    db = get_database()
    from app.services.booking_provider_resolver import list_managed_establishment_ids

    managed_ids = [
        ObjectId(i) for i in await list_managed_establishment_ids(owner_id, "transport") if ObjectId.is_valid(i)
    ]
    query = {"$or": [{"owner_id": owner_id}, {"_id": {"$in": managed_ids}}]} if managed_ids else {"owner_id": owner_id}
    docs = await db[PROVIDERS_COLLECTION].find(query).to_list(length=None)
    return [_provider_to_detail(d) for d in docs]


async def get_provider(provider_id: str) -> TransportProviderDetail:
    db = get_database()
    doc = await find_by_slug_or_id(db, PROVIDERS_COLLECTION, provider_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestataire de transport introuvable")
    return _provider_to_detail(doc)


async def update_provider(provider_id: str, data: UpdateTransportProviderRequest, current_user_id: str, is_admin: bool) -> TransportProviderDetail:
    db = get_database()
    if not ObjectId.is_valid(provider_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestataire de transport introuvable")
    doc = await db[PROVIDERS_COLLECTION].find_one({"_id": ObjectId(provider_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestataire de transport introuvable")
    if not is_admin:
        from app.services.booking_provider_resolver import is_authorized_for_establishment

        if not await is_authorized_for_establishment("transport", provider_id, current_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez modifier que votre propre profil")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[PROVIDERS_COLLECTION].update_one({"_id": ObjectId(provider_id)}, {"$set": update_fields})

    return await get_provider(provider_id)


async def set_verification_status(provider_id: str, is_verified: bool) -> TransportProviderDetail:
    db = get_database()
    if not ObjectId.is_valid(provider_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestataire de transport introuvable")
    result = await db[PROVIDERS_COLLECTION].update_one(
        {"_id": ObjectId(provider_id)},
        {"$set": {"is_verified": is_verified, "status": TransportProviderStatus.ACTIVE.value, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestataire de transport introuvable")
    return await get_provider(provider_id)


async def delete_provider(provider_id: str, current_user_id: str, is_admin: bool) -> None:
    db = get_database()
    if not ObjectId.is_valid(provider_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestataire de transport introuvable")
    doc = await db[PROVIDERS_COLLECTION].find_one({"_id": ObjectId(provider_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestataire de transport introuvable")
    if doc["owner_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que votre propre profil")
    await db[PROVIDERS_COLLECTION].delete_one({"_id": ObjectId(provider_id)})


# --- Trajets ---

def _trip_to_response(doc: dict) -> TripRequestResponse:
    return TripRequestResponse(
        id=str(doc["_id"]),
        passenger_id=doc["passenger_id"],
        provider_id=doc["provider_id"],
        type=doc["type"],
        pickup_location=doc["pickup_location"],
        pickup_address=doc.get("pickup_address"),
        dropoff_location=doc.get("dropoff_location"),
        dropoff_address=doc.get("dropoff_address"),
        scheduled_at=doc.get("scheduled_at"),
        estimated_price=doc.get("estimated_price"),
        price_currency=doc.get("price_currency", "XOF"),
        status=doc.get("status", TripRequestStatus.REQUESTED.value),
        created_at=doc["created_at"],
    )


async def create_trip_request(data: CreateTripRequest, passenger_id: str) -> TripRequestResponse:
    provider = await get_provider(data.provider_id)  # 404 si inexistant

    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["passenger_id"] = passenger_id
    doc["estimated_price"] = provider.price_estimate
    doc["price_currency"] = provider.price_currency
    doc["status"] = TripRequestStatus.REQUESTED.value
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[TRIPS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _trip_to_response(doc)


async def get_trip_request(trip_id: str, current_user_id: str, is_admin: bool) -> TripRequestResponse:
    db = get_database()
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trajet introuvable")
    doc = await db[TRIPS_COLLECTION].find_one({"_id": ObjectId(trip_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trajet introuvable")
    if doc["passenger_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à ce trajet")
    return _trip_to_response(doc)


async def list_my_trips(passenger_id: str) -> list:
    db = get_database()
    docs = await db[TRIPS_COLLECTION].find({"passenger_id": passenger_id}).sort("created_at", -1).to_list(length=None)
    return [_trip_to_response(d) for d in docs]


async def update_trip_status(trip_id: str, new_status: TripRequestStatus, current_user_id: str, is_admin: bool) -> TripRequestResponse:
    db = get_database()
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trajet introuvable")
    doc = await db[TRIPS_COLLECTION].find_one({"_id": ObjectId(trip_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trajet introuvable")

    provider = await get_provider(doc["provider_id"])
    is_provider_owner = provider.owner_id == current_user_id
    is_passenger = doc["passenger_id"] == current_user_id
    if not (is_provider_owner or is_passenger or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à ce trajet")

    await db[TRIPS_COLLECTION].update_one(
        {"_id": ObjectId(trip_id)},
        {"$set": {"status": new_status.value, "updated_at": datetime.utcnow()}},
    )
    doc = await db[TRIPS_COLLECTION].find_one({"_id": ObjectId(trip_id)})
    return _trip_to_response(doc)
