from datetime import datetime, date
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.hotel import AccommodationType, HotelStatus
from app.schemas.hotel import (
    CreateHotelRequest,
    UpdateHotelRequest,
    HotelSummary,
    HotelDetail,
    HotelListResponse,
    AvailabilityCheckRequest,
    AvailabilityCheckResponse,
    RoomAvailability,
)

COLLECTION = "hotels"
BOOKINGS_COLLECTION = "hotel_room_bookings"  # alimentée par le futur module Réservation (§33)


def _to_summary(doc: dict) -> HotelSummary:
    prices = [rt["price_per_night"] for rt in doc.get("room_types", [])]
    return HotelSummary(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc["type"],
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        photo=doc["photos"][0] if doc.get("photos") else None,
        min_price=min(prices) if prices else None,
        currency=doc.get("room_types", [{}])[0].get("currency", "XOF") if doc.get("room_types") else "XOF",
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        is_verified=doc.get("is_verified", False),
    )


def _to_detail(doc: dict) -> HotelDetail:
    return HotelDetail(
        id=str(doc["_id"]),
        owner_id=doc["owner_id"],
        name=doc["name"],
        type=doc["type"],
        description=doc["description"],
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        location=doc["location"],
        address=doc.get("address"),
        photos=doc.get("photos", []),
        videos=doc.get("videos", []),
        photos_360=doc.get("photos_360", []),
        amenities=doc.get("amenities", []),
        room_types=doc.get("room_types", []),
        offers=doc.get("offers", []),
        contact_phone=doc.get("contact_phone"),
        contact_email=doc.get("contact_email"),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        is_verified=doc.get("is_verified", False),
        status=doc.get("status", HotelStatus.DRAFT.value),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_hotel(data: CreateHotelRequest, owner_id: str, is_admin: bool = False) -> HotelDetail:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["owner_id"] = owner_id
    doc["offers"] = []
    doc["average_rating"] = 0.0
    doc["review_count"] = 0
    doc["is_verified"] = False

    if is_admin:
        doc["status"] = HotelStatus.PUBLISHED.value
    else:
        from app.services import user_service
        owner = await user_service.get_user_by_id(owner_id)
        doc["status"] = HotelStatus.PUBLISHED.value if owner.is_verified else HotelStatus.DRAFT.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_at"] = now
    doc["updated_at"] = now

    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_hotels(
    type: Optional[AccommodationType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    city: Optional[str] = None,
    max_price: Optional[float] = None,
    amenity: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> HotelListResponse:
    db = get_database()
    query: dict = {"status": HotelStatus.PUBLISHED.value}

    if type:
        query["type"] = type.value if isinstance(type, AccommodationType) else type
    if region:
        query["region"] = region
    if province:
        query["province"] = province
    if city:
        query["city"] = city
    if amenity:
        query["amenities"] = amenity
    if max_price is not None:
        query["room_types.price_per_night"] = {"$lte": max_price}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]

    total = await db[COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    cursor = db[COLLECTION].find(query).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    return HotelListResponse(
        items=[_to_summary(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def list_my_hotels(owner_id: str) -> list:
    db = get_database()
    from app.services.booking_provider_resolver import list_managed_establishment_ids

    managed_ids = [ObjectId(i) for i in await list_managed_establishment_ids(owner_id, "hotel") if ObjectId.is_valid(i)]
    query = {"$or": [{"owner_id": owner_id}, {"_id": {"$in": managed_ids}}]} if managed_ids else {"owner_id": owner_id}
    docs = await db[COLLECTION].find(query).to_list(length=None)
    return [_to_detail(d) for d in docs]


async def get_hotel(hotel_id: str) -> HotelDetail:
    db = get_database()
    if not ObjectId.is_valid(hotel_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hébergement introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(hotel_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hébergement introuvable")
    return _to_detail(doc)


async def update_hotel(hotel_id: str, data: UpdateHotelRequest, current_user_id: str, is_admin: bool) -> HotelDetail:
    db = get_database()
    if not ObjectId.is_valid(hotel_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hébergement introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(hotel_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hébergement introuvable")
    if not is_admin:
        from app.services.booking_provider_resolver import is_authorized_for_establishment

        if not await is_authorized_for_establishment("hotel", hotel_id, current_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez modifier que vos propres hébergements")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[COLLECTION].update_one({"_id": ObjectId(hotel_id)}, {"$set": update_fields})

    return await get_hotel(hotel_id)


async def delete_hotel(hotel_id: str, current_user_id: str, is_admin: bool) -> None:
    db = get_database()
    if not ObjectId.is_valid(hotel_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hébergement introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(hotel_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hébergement introuvable")
    if doc["owner_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres hébergements")
    await db[COLLECTION].delete_one({"_id": ObjectId(hotel_id)})


async def check_availability(hotel_id: str, data: AvailabilityCheckRequest) -> AvailabilityCheckResponse:
    hotel = await get_hotel(hotel_id)
    db = get_database()

    check_in_str = data.check_in.isoformat()
    check_out_str = data.check_out.isoformat()

    room_types = hotel.room_types
    if data.room_type_name:
        room_types = [rt for rt in room_types if rt.name == data.room_type_name]

    results = []
    for rt in room_types:
        overlapping = await db[BOOKINGS_COLLECTION].count_documents({
            "hotel_id": hotel_id,
            "room_type_name": rt.name,
            "check_in": {"$lt": check_out_str},
            "check_out": {"$gt": check_in_str},
        })
        results.append(RoomAvailability(
            room_type_name=rt.name,
            total_rooms=rt.total_rooms,
            booked_rooms=overlapping,
            available_rooms=max(0, rt.total_rooms - overlapping),
            price_per_night=rt.price_per_night,
            currency=rt.currency,
        ))

    return AvailabilityCheckResponse(check_in=data.check_in, check_out=data.check_out, rooms=results)
