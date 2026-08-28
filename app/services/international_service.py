from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.international import FirstVisitGuideCategory
from app.schemas.international import (
    CreateGuideEntryRequest,
    UpdateGuideEntryRequest,
    GuideEntryResponse,
    SupportedLanguageResponse,
)

GUIDE_COLLECTION = "first_visit_guide"
LANGUAGES_COLLECTION = "supported_languages"

DEFAULT_LANGUAGES = [{"code": "fr", "label": "Français", "is_active": True}]


def _entry_to_response(doc: dict) -> GuideEntryResponse:
    return GuideEntryResponse(
        id=str(doc["_id"]),
        category=doc["category"],
        title=doc["title"],
        content=doc["content"],
        language=doc.get("language", "fr"),
        updated_at=doc["updated_at"],
    )


async def create_guide_entry(data: CreateGuideEntryRequest) -> GuideEntryResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[GUIDE_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _entry_to_response(doc)


async def list_guide_entries(
    category: Optional[FirstVisitGuideCategory] = None,
    language: str = "fr",
) -> list:
    db = get_database()
    query: dict = {"language": language}
    if category:
        query["category"] = category.value if isinstance(category, FirstVisitGuideCategory) else category
    docs = await db[GUIDE_COLLECTION].find(query).to_list(length=None)
    return [_entry_to_response(d) for d in docs]


async def update_guide_entry(entry_id: str, data: UpdateGuideEntryRequest) -> GuideEntryResponse:
    db = get_database()
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[GUIDE_COLLECTION].update_one({"_id": ObjectId(entry_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée introuvable")
    doc = await db[GUIDE_COLLECTION].find_one({"_id": ObjectId(entry_id)})
    return _entry_to_response(doc)


async def delete_guide_entry(entry_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée introuvable")
    result = await db[GUIDE_COLLECTION].delete_one({"_id": ObjectId(entry_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée introuvable")


# --- Langues supportées ---

async def list_supported_languages() -> list:
    db = get_database()
    count = await db[LANGUAGES_COLLECTION].count_documents({})
    if count == 0:
        await db[LANGUAGES_COLLECTION].insert_many(DEFAULT_LANGUAGES.copy())
    docs = await db[LANGUAGES_COLLECTION].find({}).to_list(length=None)
    return [SupportedLanguageResponse(code=d["code"], label=d["label"], is_active=d.get("is_active", True)) for d in docs]


async def set_language_active(code: str, is_active: bool) -> SupportedLanguageResponse:
    db = get_database()
    result = await db[LANGUAGES_COLLECTION].update_one({"code": code}, {"$set": {"is_active": is_active}})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Langue introuvable")
    doc = await db[LANGUAGES_COLLECTION].find_one({"code": code})
    return SupportedLanguageResponse(code=doc["code"], label=doc["label"], is_active=doc.get("is_active", True))
