from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.booking import BookingStatus
from app.models.review import ReviewTargetType, ReviewStatus
from app.schemas.review import (
    CreateReviewRequest,
    UpdateReviewRequest,
    ReplyReviewRequest,
    ReportReviewRequest,
    ModerateReviewRequest,
    ReviewResponse,
    ReviewListResponse,
)

COLLECTION = "reviews"
BOOKINGS_COLLECTION = "bookings"
USERS_COLLECTION = "users"

# Cible -> (collection du profil, champ id du propriétaire pour l'autorisation de réponse)
TARGET_COLLECTIONS = {
    ReviewTargetType.GUIDE.value: "guide_profiles",
    ReviewTargetType.HOTEL.value: "hotels",
    ReviewTargetType.RESTAURANT.value: "restaurants",
    ReviewTargetType.TRANSPORT.value: "transport_providers",
    ReviewTargetType.DESTINATION.value: "destinations",
    ReviewTargetType.EVENT.value: "events",
    ReviewTargetType.ARTISAN_PRODUCT.value: "artisan_products",
}

# item_type de Booking -> ReviewTargetType (les valeurs se recouvrent déjà pour la plupart)
BOOKING_ITEM_TO_TARGET = {
    "guide": ReviewTargetType.GUIDE.value,
    "hotel": ReviewTargetType.HOTEL.value,
    "restaurant": ReviewTargetType.RESTAURANT.value,
    "transport": ReviewTargetType.TRANSPORT.value,
    "visit": ReviewTargetType.DESTINATION.value,
    "event": ReviewTargetType.EVENT.value,
}


def _to_response(doc: dict, author: Optional[dict] = None) -> ReviewResponse:
    return ReviewResponse(
        id=str(doc["_id"]),
        target_type=doc["target_type"],
        target_id=doc["target_id"],
        author_id=doc["author_id"],
        author_name=author.get("full_name") if author else None,
        author_avatar_url=author.get("avatar_url") if author else None,
        booking_id=doc["booking_id"],
        rating=doc["rating"],
        comment=doc.get("comment"),
        photos=doc.get("photos", []),
        reply_comment=doc.get("reply_comment"),
        reply_at=doc.get("reply_at"),
        status=doc.get("status", ReviewStatus.PUBLISHED.value),
        report_count=len(doc.get("reports", [])),
        helpful_count=doc.get("helpful_count", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def _recompute_target_aggregate(target_type: str, target_id: str) -> None:
    """Recalcule average_rating/review_count et les persiste sur le profil cible."""
    db = get_database()
    collection_name = TARGET_COLLECTIONS.get(target_type)
    if not collection_name or not ObjectId.is_valid(target_id):
        return

    pipeline = [
        {"$match": {"target_type": target_type, "target_id": target_id, "status": ReviewStatus.PUBLISHED.value}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    result = await db[COLLECTION].aggregate(pipeline).to_list(length=1)
    avg = round(result[0]["avg"], 1) if result else 0.0
    count = result[0]["count"] if result else 0

    await db[collection_name].update_one(
        {"_id": ObjectId(target_id)},
        {"$set": {"average_rating": avg, "review_count": count}},
    )


async def create_review(data: CreateReviewRequest, author_id: str) -> ReviewResponse:
    db = get_database()
    if not ObjectId.is_valid(data.booking_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")

    booking = await db[BOOKINGS_COLLECTION].find_one({"_id": ObjectId(data.booking_id)})
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    if booking["customer_id"] != author_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette réservation ne vous appartient pas")
    if booking.get("status") != BookingStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Seule une réservation terminée peut faire l'objet d'un avis",
        )

    existing = await db[COLLECTION].find_one({"booking_id": data.booking_id})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un avis existe déjà pour cette réservation")

    target_type = BOOKING_ITEM_TO_TARGET.get(booking["item_type"])
    if not target_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce type de réservation ne peut pas recevoir d'avis")

    now = datetime.utcnow()
    doc = {
        "target_type": target_type,
        "target_id": booking["item_id"],
        "author_id": author_id,
        "booking_id": data.booking_id,
        "rating": data.rating,
        "comment": data.comment,
        "photos": data.photos,
        "reply_comment": None,
        "reply_at": None,
        "status": ReviewStatus.PUBLISHED.value,
        "reports": [],
        "helpful_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    await _recompute_target_aggregate(target_type, booking["item_id"])

    author = await db[USERS_COLLECTION].find_one({"_id": ObjectId(author_id)}) if ObjectId.is_valid(author_id) else None
    return _to_response(doc, author)


async def list_reviews_for_target(
    target_type: str, target_id: str, page: int = 1, page_size: int = 20
) -> ReviewListResponse:
    db = get_database()
    query = {"target_type": target_type, "target_id": target_id, "status": ReviewStatus.PUBLISHED.value}

    total = await db[COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    docs = await db[COLLECTION].find(query).sort("created_at", -1).skip(skip).limit(page_size).to_list(length=page_size)

    author_ids = {d["author_id"] for d in docs if ObjectId.is_valid(d["author_id"])}
    author_docs = await db[USERS_COLLECTION].find({"_id": {"$in": [ObjectId(a) for a in author_ids]}}).to_list(length=None)
    authors_by_id = {str(a["_id"]): a for a in author_docs}

    items = [_to_response(d, authors_by_id.get(d["author_id"])) for d in docs]

    all_published = await db[COLLECTION].find(
        {"target_type": target_type, "target_id": target_id, "status": ReviewStatus.PUBLISHED.value}
    ).to_list(length=None)
    breakdown = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for d in all_published:
        breakdown[str(d["rating"])] = breakdown.get(str(d["rating"]), 0) + 1
    average = round(sum(d["rating"] for d in all_published) / len(all_published), 1) if all_published else 0.0

    return ReviewListResponse(
        items=items, total=total, page=page, page_size=page_size,
        average_rating=average, rating_breakdown=breakdown,
    )


async def list_my_reviews(author_id: str) -> list:
    db = get_database()
    docs = await db[COLLECTION].find({"author_id": author_id}).sort("created_at", -1).to_list(length=None)
    author = await db[USERS_COLLECTION].find_one({"_id": ObjectId(author_id)}) if ObjectId.is_valid(author_id) else None
    return [_to_response(d, author) for d in docs]


async def get_review(review_id: str) -> ReviewResponse:
    db = get_database()
    if not ObjectId.is_valid(review_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(review_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")
    author = await db[USERS_COLLECTION].find_one({"_id": ObjectId(doc["author_id"])}) if ObjectId.is_valid(doc["author_id"]) else None
    return _to_response(doc, author)


async def update_review(review_id: str, data: UpdateReviewRequest, author_id: str) -> ReviewResponse:
    db = get_database()
    if not ObjectId.is_valid(review_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(review_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")
    if doc["author_id"] != author_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez modifier que vos propres avis")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[COLLECTION].update_one({"_id": ObjectId(review_id)}, {"$set": update_fields})
        if "rating" in update_fields:
            await _recompute_target_aggregate(doc["target_type"], doc["target_id"])

    return await get_review(review_id)


async def delete_review(review_id: str, author_id: str, is_admin: bool = False) -> None:
    db = get_database()
    if not ObjectId.is_valid(review_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(review_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")
    if doc["author_id"] != author_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres avis")

    await db[COLLECTION].delete_one({"_id": ObjectId(review_id)})
    await _recompute_target_aggregate(doc["target_type"], doc["target_id"])


async def reply_to_review(review_id: str, data: ReplyReviewRequest, current_user_id: str, is_admin: bool = False) -> ReviewResponse:
    """Seul le propriétaire de la cible (ex: le guide concerné) ou un admin peut répondre."""
    db = get_database()
    if not ObjectId.is_valid(review_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(review_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")

    if not is_admin:
        collection_name = TARGET_COLLECTIONS.get(doc["target_type"])
        target_doc = await db[collection_name].find_one({"_id": ObjectId(doc["target_id"])}) if collection_name and ObjectId.is_valid(doc["target_id"]) else None
        owner_field = "user_id" if "user_id" in (target_doc or {}) else "owner_id"
        if not target_doc or target_doc.get(owner_field) != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez répondre qu'aux avis vous concernant")

    await db[COLLECTION].update_one(
        {"_id": ObjectId(review_id)},
        {"$set": {"reply_comment": data.reply_comment, "reply_at": datetime.utcnow(), "updated_at": datetime.utcnow()}},
    )
    return await get_review(review_id)


async def report_review(review_id: str, data: ReportReviewRequest, reporter_id: str) -> ReviewResponse:
    db = get_database()
    if not ObjectId.is_valid(review_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")

    report = {
        "reporter_id": reporter_id,
        "reason": data.reason.value if hasattr(data.reason, "value") else data.reason,
        "comment": data.comment,
        "created_at": datetime.utcnow(),
    }
    result = await db[COLLECTION].update_one(
        {"_id": ObjectId(review_id)},
        {"$push": {"reports": report}, "$set": {"updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")

    # Signalement automatique en file de modération à partir de 3 signalements distincts
    doc = await db[COLLECTION].find_one({"_id": ObjectId(review_id)})
    if len(doc.get("reports", [])) >= 3 and doc.get("status") == ReviewStatus.PUBLISHED.value:
        await db[COLLECTION].update_one(
            {"_id": ObjectId(review_id)}, {"$set": {"status": ReviewStatus.FLAGGED.value}}
        )
        await _recompute_target_aggregate(doc["target_type"], doc["target_id"])

    return await get_review(review_id)


async def list_flagged_reviews() -> list:
    """(Admin) File de modération des avis signalés."""
    db = get_database()
    docs = await db[COLLECTION].find({"status": ReviewStatus.FLAGGED.value}).sort("updated_at", -1).to_list(length=None)
    author_ids = {d["author_id"] for d in docs if ObjectId.is_valid(d["author_id"])}
    author_docs = await db[USERS_COLLECTION].find({"_id": {"$in": [ObjectId(a) for a in author_ids]}}).to_list(length=None)
    authors_by_id = {str(a["_id"]): a for a in author_docs}
    return [_to_response(d, authors_by_id.get(d["author_id"])) for d in docs]


async def moderate_review(review_id: str, data: ModerateReviewRequest) -> ReviewResponse:
    """(Admin) Republier ou masquer définitivement un avis signalé."""
    db = get_database()
    if not ObjectId.is_valid(review_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(review_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")

    await db[COLLECTION].update_one(
        {"_id": ObjectId(review_id)},
        {"$set": {"status": data.status.value, "updated_at": datetime.utcnow()}},
    )
    await _recompute_target_aggregate(doc["target_type"], doc["target_id"])
    return await get_review(review_id)


async def mark_helpful(review_id: str) -> ReviewResponse:
    db = get_database()
    if not ObjectId.is_valid(review_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")
    result = await db[COLLECTION].update_one({"_id": ObjectId(review_id)}, {"$inc": {"helpful_count": 1}})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avis introuvable")
    return await get_review(review_id)
