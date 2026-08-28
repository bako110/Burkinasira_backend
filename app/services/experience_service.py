from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.experience import ExperienceType, ExperienceStatus
from app.schemas.experience import (
    CreateExperienceRequest,
    UpdateExperienceRequest,
    ExperienceSummary,
    ExperienceDetail,
    ExperienceListResponse,
)

COLLECTION = "experiences"


def _to_summary(doc: dict) -> ExperienceSummary:
    return ExperienceSummary(
        id=str(doc["_id"]),
        title=doc["title"],
        type=doc["type"],
        host_name=doc["host_name"],
        region=doc["region"],
        city=doc.get("city"),
        photo=doc["photos"][0] if doc.get("photos") else None,
        price_amount=doc.get("price_amount"),
        price_currency=doc.get("price_currency", "XOF"),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
    )


def _to_detail(doc: dict) -> ExperienceDetail:
    return ExperienceDetail(
        id=str(doc["_id"]),
        title=doc["title"],
        description=doc["description"],
        type=doc["type"],
        host_id=doc["host_id"],
        host_name=doc["host_name"],
        region=doc["region"],
        city=doc.get("city"),
        location=doc["location"],
        photos=doc.get("photos", []),
        duration_minutes=doc.get("duration_minutes"),
        max_participants=doc.get("max_participants"),
        price_amount=doc.get("price_amount"),
        price_currency=doc.get("price_currency", "XOF"),
        languages=doc.get("languages", []),
        revenue_share=doc.get("revenue_share"),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_experience(data: CreateExperienceRequest, host_id: str, host_name: str) -> ExperienceDetail:
    db = get_database()
    now = datetime.utcnow()

    doc = data.model_dump()
    doc["host_id"] = host_id
    doc["host_name"] = host_name
    doc["average_rating"] = 0.0
    doc["review_count"] = 0
    doc["status"] = ExperienceStatus.PUBLISHED.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_at"] = now
    doc["updated_at"] = now

    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_experiences(
    type: Optional[ExperienceType] = None,
    region: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> ExperienceListResponse:
    db = get_database()
    query: dict = {"status": ExperienceStatus.PUBLISHED.value}

    if type:
        query["type"] = type.value if isinstance(type, ExperienceType) else type
    if region:
        query["region"] = region
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]

    total = await db[COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    cursor = db[COLLECTION].find(query).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    return ExperienceListResponse(
        items=[_to_summary(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_experience(experience_id: str) -> ExperienceDetail:
    db = get_database()
    if not ObjectId.is_valid(experience_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expérience introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(experience_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expérience introuvable")
    return _to_detail(doc)


async def update_experience(experience_id: str, data: UpdateExperienceRequest, current_user_id: str, is_admin: bool) -> ExperienceDetail:
    db = get_database()
    if not ObjectId.is_valid(experience_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expérience introuvable")

    doc = await db[COLLECTION].find_one({"_id": ObjectId(experience_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expérience introuvable")
    if doc["host_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez modifier que vos propres expériences")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[COLLECTION].update_one({"_id": ObjectId(experience_id)}, {"$set": update_fields})

    return await get_experience(experience_id)


async def delete_experience(experience_id: str, current_user_id: str, is_admin: bool) -> None:
    db = get_database()
    if not ObjectId.is_valid(experience_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expérience introuvable")

    doc = await db[COLLECTION].find_one({"_id": ObjectId(experience_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expérience introuvable")
    if doc["host_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres expériences")

    await db[COLLECTION].delete_one({"_id": ObjectId(experience_id)})
