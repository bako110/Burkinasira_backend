from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.guide import GuideStatus
from app.schemas.guide import (
    CreateGuideProfileRequest,
    UpdateGuideProfileRequest,
    GuideSummary,
    GuideDetail,
    GuideListResponse,
)

COLLECTION = "guide_profiles"


def _to_summary(doc: dict) -> GuideSummary:
    return GuideSummary(
        id=str(doc["_id"]),
        display_name=doc["display_name"],
        photo_url=doc.get("photo_url"),
        languages=doc.get("languages", []),
        specialties=doc.get("specialties", []),
        regions_covered=doc.get("regions_covered", []),
        is_verified=doc.get("is_verified", False),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        daily_rate=doc.get("daily_rate"),
        currency=doc.get("currency", "XOF"),
    )


def _to_detail(doc: dict) -> GuideDetail:
    return GuideDetail(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        display_name=doc["display_name"],
        bio=doc.get("bio"),
        photo_url=doc.get("photo_url"),
        languages=doc.get("languages", []),
        specialties=doc.get("specialties", []),
        regions_covered=doc.get("regions_covered", []),
        certifications=doc.get("certifications", []),
        hourly_rate=doc.get("hourly_rate"),
        daily_rate=doc.get("daily_rate"),
        currency=doc.get("currency", "XOF"),
        is_verified=doc.get("is_verified", False),
        status=doc.get("status", GuideStatus.PENDING.value),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        visits_completed=doc.get("visits_completed", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_guide_profile(data: CreateGuideProfileRequest, user_id: str) -> GuideDetail:
    db = get_database()
    existing = await db[COLLECTION].find_one({"user_id": user_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un profil guide existe déjà pour ce compte",
        )

    now = datetime.utcnow()
    doc = data.model_dump()
    doc["user_id"] = user_id
    doc["is_verified"] = False
    doc["status"] = GuideStatus.PENDING.value
    doc["average_rating"] = 0.0
    doc["review_count"] = 0
    doc["visits_completed"] = 0
    doc["created_at"] = now
    doc["updated_at"] = now

    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_guides(
    region: Optional[str] = None,
    language: Optional[str] = None,
    specialty: Optional[str] = None,
    verified_only: bool = False,
    include_all_statuses: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> GuideListResponse:
    db = get_database()
    query: dict = {} if include_all_statuses else {"status": GuideStatus.ACTIVE.value}

    if region:
        query["regions_covered"] = region
    if language:
        query["languages"] = language
    if specialty:
        query["specialties"] = specialty
    if verified_only:
        query["is_verified"] = True

    total = await db[COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    cursor = db[COLLECTION].find(query).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    return GuideListResponse(
        items=[_to_summary(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_guide(guide_id: str) -> GuideDetail:
    db = get_database()
    if not ObjectId.is_valid(guide_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guide introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(guide_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guide introuvable")
    return _to_detail(doc)


async def get_guide_by_user_id(user_id: str) -> GuideDetail:
    db = get_database()
    doc = await db[COLLECTION].find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil guide introuvable")
    return _to_detail(doc)


async def update_guide_profile(user_id: str, data: UpdateGuideProfileRequest) -> GuideDetail:
    db = get_database()
    doc = await db[COLLECTION].find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil guide introuvable")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[COLLECTION].update_one({"_id": doc["_id"]}, {"$set": update_fields})

    return await get_guide(str(doc["_id"]))


async def set_verification_status(guide_id: str, is_verified: bool) -> GuideDetail:
    """(Admin) Vérifier ou retirer la vérification d'un guide (§37 GoTours Verified)."""
    db = get_database()
    if not ObjectId.is_valid(guide_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guide introuvable")
    result = await db[COLLECTION].update_one(
        {"_id": ObjectId(guide_id)},
        {"$set": {"is_verified": is_verified, "status": GuideStatus.ACTIVE.value, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guide introuvable")
    return await get_guide(guide_id)


async def delete_guide_profile(user_id: str, is_admin: bool = False, target_guide_id: Optional[str] = None) -> None:
    db = get_database()
    if target_guide_id:
        if not ObjectId.is_valid(target_guide_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil guide introuvable")
        doc = await db[COLLECTION].find_one({"_id": ObjectId(target_guide_id)})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil guide introuvable")
        if doc["user_id"] != user_id and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que votre propre profil")
        await db[COLLECTION].delete_one({"_id": ObjectId(target_guide_id)})
        return

    result = await db[COLLECTION].delete_one({"user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil guide introuvable")
