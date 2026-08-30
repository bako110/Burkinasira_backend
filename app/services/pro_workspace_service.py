from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.booking import BookingStatus
from app.models.pro_workspace import PromotionStatus
from app.schemas.pro_workspace import (
    ProDashboardResponse,
    CreatePromotionRequest,
    PromotionResponse,
    InviteTeamMemberRequest,
    TeamMemberResponse,
)

PROMOTIONS_COLLECTION = "pro_promotions"
TEAM_COLLECTION = "pro_team_members"

# Collections possédées par un provider, indexées par item_type de Booking
OWNED_ITEM_COLLECTIONS = {
    "hotel": "hotels",
    "restaurant": "restaurants",
    "activity": "experiences",
    "experience": "experiences",
}


async def _get_owned_item_ids(provider_id: str) -> dict:
    """Retourne {item_type: [item_ids]} pour tout ce que possède ce provider."""
    db = get_database()
    owned = {}
    for item_type, collection_name in OWNED_ITEM_COLLECTIONS.items():
        docs = await db[collection_name].find({"owner_id": provider_id}, {"_id": 1}).to_list(length=None)
        owned.setdefault(item_type, set()).update(str(d["_id"]) for d in docs)
    return owned


async def get_dashboard(provider_id: str) -> ProDashboardResponse:
    db = get_database()
    owned = await _get_owned_item_ids(provider_id)

    all_item_ids = set()
    for ids in owned.values():
        all_item_ids.update(ids)

    if not all_item_ids:
        return ProDashboardResponse(
            provider_id=provider_id, total_bookings=0, pending_bookings=0,
            confirmed_bookings=0, total_revenue=0.0, currency="XOF",
            average_rating=0.0, review_count=0,
        )

    bookings = await db["bookings"].find({"item_id": {"$in": list(all_item_ids)}}).to_list(length=None)

    total_revenue = sum(
        b["total_price"] for b in bookings if b.get("status") in (BookingStatus.CONFIRMED.value, BookingStatus.COMPLETED.value)
    )
    pending = sum(1 for b in bookings if b.get("status") == BookingStatus.PENDING.value)
    confirmed = sum(1 for b in bookings if b.get("status") == BookingStatus.CONFIRMED.value)

    ratings = []
    review_count = 0
    for item_type, collection_name in OWNED_ITEM_COLLECTIONS.items():
        item_ids = owned.get(item_type, set())
        if not item_ids:
            continue
        docs = await db[collection_name].find(
            {"_id": {"$in": [ObjectId(i) for i in item_ids]}}
        ).to_list(length=None)
        for d in docs:
            if d.get("review_count", 0) > 0:
                ratings.append(d["average_rating"] * d["review_count"])
                review_count += d["review_count"]

    average_rating = round(sum(ratings) / review_count, 2) if review_count else 0.0

    return ProDashboardResponse(
        provider_id=provider_id,
        total_bookings=len(bookings),
        pending_bookings=pending,
        confirmed_bookings=confirmed,
        total_revenue=total_revenue,
        currency="XOF",
        average_rating=average_rating,
        review_count=review_count,
    )


# --- Promotions ---

def _promo_to_response(doc: dict) -> PromotionResponse:
    return PromotionResponse(
        id=str(doc["_id"]),
        provider_id=doc["provider_id"],
        title=doc["title"],
        description=doc.get("description"),
        discount_percent=doc.get("discount_percent"),
        applies_to_item_type=doc["applies_to_item_type"],
        applies_to_item_id=doc["applies_to_item_id"],
        valid_from=doc["valid_from"],
        valid_until=doc["valid_until"],
        status=doc.get("status", PromotionStatus.ACTIVE.value),
    )


async def create_promotion(data: CreatePromotionRequest, provider_id: str) -> PromotionResponse:
    db = get_database()
    doc = data.model_dump()
    doc["provider_id"] = provider_id
    doc["status"] = PromotionStatus.ACTIVE.value
    doc["created_at"] = datetime.utcnow()
    result = await db[PROMOTIONS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _promo_to_response(doc)


async def list_my_promotions(provider_id: str) -> list:
    db = get_database()
    docs = await db[PROMOTIONS_COLLECTION].find({"provider_id": provider_id}).to_list(length=None)
    return [_promo_to_response(d) for d in docs]


# --- Équipe ---

def _team_member_to_response(doc: dict, account_created: bool = False) -> TeamMemberResponse:
    return TeamMemberResponse(
        id=str(doc["_id"]),
        provider_id=doc["provider_id"],
        user_id=doc.get("user_id"),
        email=doc["email"],
        role=doc.get("role", "staff"),
        establishment_type=doc.get("establishment_type"),
        establishment_id=doc.get("establishment_id"),
        is_active=doc.get("is_active", True),
        account_created=account_created,
    )


async def invite_team_member(data: InviteTeamMemberRequest, provider_id: str) -> TeamMemberResponse:
    db = get_database()

    if data.establishment_type and data.establishment_id:
        from app.services.booking_provider_resolver import resolve_owner_id

        owner_id = await resolve_owner_id(data.establishment_type, data.establishment_id)
        if owner_id != provider_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cet établissement ne vous appartient pas")

    existing_user = await db["users"].find_one({"email": data.email.lower()})
    account_created = False
    if existing_user:
        user_id = str(existing_user["_id"])
    else:
        from app.models.user import UserRole
        from app.services.user_service import create_managed_user

        created = await create_managed_user(
            email=data.email, password=data.temporary_password, full_name=data.full_name, role=UserRole.PROVIDER
        )
        user_id = created.id
        account_created = True

    doc = {
        "provider_id": provider_id,
        "user_id": user_id,
        "email": data.email.lower(),
        "role": data.role.value,
        "establishment_type": data.establishment_type,
        "establishment_id": data.establishment_id,
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
    result = await db[TEAM_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _team_member_to_response(doc, account_created=account_created)


async def list_team_members(provider_id: str, establishment_type: str = None, establishment_id: str = None) -> list:
    db = get_database()
    query: dict = {"provider_id": provider_id}
    if establishment_type and establishment_id:
        query["establishment_type"] = establishment_type
        query["establishment_id"] = establishment_id
    docs = await db[TEAM_COLLECTION].find(query).to_list(length=None)
    return [_team_member_to_response(d) for d in docs]


async def remove_team_member(member_id: str, provider_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(member_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable")
    doc = await db[TEAM_COLLECTION].find_one({"_id": ObjectId(member_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable")
    if doc["provider_id"] != provider_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    await db[TEAM_COLLECTION].delete_one({"_id": ObjectId(member_id)})
