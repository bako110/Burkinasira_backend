from datetime import datetime
from typing import Optional
from bson import ObjectId
from pymongo import ReturnDocument
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.impact import ImpactInitiativeCategory, ImpactInitiativeStatus
from app.schemas.impact import (
    CreateInitiativeRequest,
    UpdateInitiativeRequest,
    InitiativeResponse,
    CreateIndicatorRequest,
    IndicatorResponse,
    SupportInitiativeRequest,
)

INITIATIVES_COLLECTION = "impact_initiatives"
INDICATORS_COLLECTION = "impact_indicators"
SUPPORT_COLLECTION = "impact_support_records"


# --- Initiatives ---

def _initiative_to_response(doc: dict) -> InitiativeResponse:
    return InitiativeResponse(
        id=str(doc["_id"]),
        title=doc["title"],
        category=doc["category"],
        description=doc["description"],
        region=doc.get("region"),
        is_verified=doc.get("is_verified", False),
        cover_photo=doc.get("cover_photo"),
        supporter_count=doc.get("supporter_count", 0),
        created_at=doc["created_at"],
    )


async def create_initiative(data: CreateInitiativeRequest, created_by: str) -> InitiativeResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["is_verified"] = False
    doc["supporter_count"] = 0
    doc["status"] = ImpactInitiativeStatus.PUBLISHED.value
    doc["created_by"] = created_by
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[INITIATIVES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _initiative_to_response(doc)


async def list_initiatives(
    category: Optional[ImpactInitiativeCategory] = None,
    region: Optional[str] = None,
) -> list:
    db = get_database()
    query: dict = {"status": ImpactInitiativeStatus.PUBLISHED.value}
    if category:
        query["category"] = category.value if isinstance(category, ImpactInitiativeCategory) else category
    if region:
        query["region"] = region
    docs = await db[INITIATIVES_COLLECTION].find(query).to_list(length=None)
    return [_initiative_to_response(d) for d in docs]


async def get_initiative(initiative_id: str) -> InitiativeResponse:
    db = get_database()
    if not ObjectId.is_valid(initiative_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative introuvable")
    doc = await db[INITIATIVES_COLLECTION].find_one({"_id": ObjectId(initiative_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative introuvable")
    return _initiative_to_response(doc)


async def update_initiative(initiative_id: str, data: UpdateInitiativeRequest) -> InitiativeResponse:
    db = get_database()
    if not ObjectId.is_valid(initiative_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[INITIATIVES_COLLECTION].update_one({"_id": ObjectId(initiative_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative introuvable")
    return await get_initiative(initiative_id)


async def support_initiative(initiative_id: str, data: SupportInitiativeRequest, supporter_id: str) -> InitiativeResponse:
    await get_initiative(initiative_id)  # 404 si inexistant
    db = get_database()

    already_supported = await db[SUPPORT_COLLECTION].find_one({"initiative_id": initiative_id, "supporter_id": supporter_id})
    if not already_supported:
        await db[SUPPORT_COLLECTION].insert_one({
            "initiative_id": initiative_id,
            "supporter_id": supporter_id,
            "message": data.message,
            "created_at": datetime.utcnow(),
        })
        await db[INITIATIVES_COLLECTION].update_one({"_id": ObjectId(initiative_id)}, {"$inc": {"supporter_count": 1}})

    return await get_initiative(initiative_id)


async def delete_initiative(initiative_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(initiative_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative introuvable")
    result = await db[INITIATIVES_COLLECTION].delete_one({"_id": ObjectId(initiative_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative introuvable")


# --- Indicateurs d'impact ---

def _indicator_to_response(doc: dict) -> IndicatorResponse:
    return IndicatorResponse(
        id=str(doc["_id"]),
        label=doc["label"],
        value=doc["value"],
        unit=doc.get("unit"),
        updated_at=doc["updated_at"],
    )


async def create_or_update_indicator(data: CreateIndicatorRequest) -> IndicatorResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = await db[INDICATORS_COLLECTION].find_one_and_update(
        {"label": data.label},
        {"$set": {"value": data.value, "unit": data.unit, "updated_at": now}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return _indicator_to_response(doc)


async def list_indicators() -> list:
    db = get_database()
    docs = await db[INDICATORS_COLLECTION].find({}).to_list(length=None)
    return [_indicator_to_response(d) for d in docs]


async def delete_indicator(indicator_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(indicator_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicateur introuvable")
    result = await db[INDICATORS_COLLECTION].delete_one({"_id": ObjectId(indicator_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicateur introuvable")
