from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.cuisine import EstablishmentType, DietaryTag, CuisineStatus
from app.schemas.cuisine import (
    CreateRestaurantRequest,
    UpdateRestaurantRequest,
    RestaurantSummary,
    RestaurantDetail,
    RestaurantListResponse,
)

COLLECTION = "restaurants"


def _to_summary(doc: dict) -> RestaurantSummary:
    return RestaurantSummary(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc["type"],
        cuisine_style=doc.get("cuisine_style"),
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        photo=doc["photos"][0] if doc.get("photos") else None,
        dietary_tags=doc.get("dietary_tags", []),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
    )


def _to_detail(doc: dict) -> RestaurantDetail:
    return RestaurantDetail(
        id=str(doc["_id"]),
        owner_id=doc["owner_id"],
        name=doc["name"],
        type=doc["type"],
        description=doc["description"],
        cuisine_style=doc.get("cuisine_style"),
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        location=doc["location"],
        address=doc.get("address"),
        photos=doc.get("photos", []),
        opening_hours=doc.get("opening_hours", []),
        menu=doc.get("menu", []),
        dietary_tags=doc.get("dietary_tags", []),
        accepts_table_booking=doc.get("accepts_table_booking", True),
        offers_takeaway=doc.get("offers_takeaway", False),
        offers_cooking_workshop=doc.get("offers_cooking_workshop", False),
        contact_phone=doc.get("contact_phone"),
        contact_email=doc.get("contact_email"),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        is_verified=doc.get("is_verified", False),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_restaurant(data: CreateRestaurantRequest, owner_id: str) -> RestaurantDetail:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["owner_id"] = owner_id
    doc["average_rating"] = 0.0
    doc["review_count"] = 0
    doc["is_verified"] = False
    doc["status"] = CuisineStatus.PUBLISHED.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_at"] = now
    doc["updated_at"] = now

    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_restaurants(
    type: Optional[EstablishmentType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    city: Optional[str] = None,
    dietary_tag: Optional[DietaryTag] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> RestaurantListResponse:
    db = get_database()
    query: dict = {"status": CuisineStatus.PUBLISHED.value}

    if type:
        query["type"] = type.value if isinstance(type, EstablishmentType) else type
    if region:
        query["region"] = region
    if province:
        query["province"] = province
    if city:
        query["city"] = city
    if dietary_tag:
        query["dietary_tags"] = dietary_tag.value if isinstance(dietary_tag, DietaryTag) else dietary_tag
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"cuisine_style": {"$regex": q, "$options": "i"}},
        ]

    total = await db[COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    cursor = db[COLLECTION].find(query).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    return RestaurantListResponse(
        items=[_to_summary(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_restaurant(restaurant_id: str) -> RestaurantDetail:
    db = get_database()
    if not ObjectId.is_valid(restaurant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(restaurant_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant introuvable")
    return _to_detail(doc)


async def update_restaurant(restaurant_id: str, data: UpdateRestaurantRequest, current_user_id: str, is_admin: bool) -> RestaurantDetail:
    db = get_database()
    if not ObjectId.is_valid(restaurant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(restaurant_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant introuvable")
    if doc["owner_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez modifier que vos propres restaurants")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[COLLECTION].update_one({"_id": ObjectId(restaurant_id)}, {"$set": update_fields})

    return await get_restaurant(restaurant_id)


async def delete_restaurant(restaurant_id: str, current_user_id: str, is_admin: bool) -> None:
    db = get_database()
    if not ObjectId.is_valid(restaurant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(restaurant_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant introuvable")
    if doc["owner_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres restaurants")
    await db[COLLECTION].delete_one({"_id": ObjectId(restaurant_id)})
