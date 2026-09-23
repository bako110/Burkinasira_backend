from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.memory import MemoryStatus
from app.schemas.memory import CreateMemoryRequest, MemoryResponse, MemoryListResponse, ModerateMemoryRequest

COLLECTION = "memories"
USERS_COLLECTION = "users"


def _to_response(doc: dict, author: Optional[dict] = None) -> MemoryResponse:
    return MemoryResponse(
        id=str(doc["_id"]),
        target_type=doc["target_type"],
        target_id=doc["target_id"],
        author_id=doc["author_id"],
        author_name=author.get("full_name") if author else None,
        author_avatar_url=author.get("avatar_url") if author else None,
        media_url=doc["media_url"],
        media_type=doc["media_type"],
        title=doc.get("title"),
        caption=doc.get("caption"),
        status=doc.get("status", MemoryStatus.PUBLISHED.value),
        created_at=doc["created_at"],
    )


async def create_memory(data: CreateMemoryRequest, author_id: str) -> MemoryResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = {
        "target_type": data.target_type.value if hasattr(data.target_type, "value") else data.target_type,
        "target_id": data.target_id,
        "author_id": author_id,
        "media_url": data.media_url,
        "media_type": data.media_type.value if hasattr(data.media_type, "value") else data.media_type,
        "title": data.title,
        "caption": data.caption,
        "status": MemoryStatus.PUBLISHED.value,
        "created_at": now,
    }
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    author = await db[USERS_COLLECTION].find_one({"_id": ObjectId(author_id)}) if ObjectId.is_valid(author_id) else None
    return _to_response(doc, author)


async def list_memories_for_target(
    target_type: str, target_id: str, page: int = 1, page_size: int = 24
) -> MemoryListResponse:
    db = get_database()
    query = {"target_type": target_type, "target_id": target_id, "status": MemoryStatus.PUBLISHED.value}

    total = await db[COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    docs = await db[COLLECTION].find(query).sort("created_at", -1).skip(skip).limit(page_size).to_list(length=page_size)

    author_ids = {d["author_id"] for d in docs if ObjectId.is_valid(d["author_id"])}
    author_docs = await db[USERS_COLLECTION].find({"_id": {"$in": [ObjectId(a) for a in author_ids]}}).to_list(length=None)
    authors_by_id = {str(a["_id"]): a for a in author_docs}

    items = [_to_response(d, authors_by_id.get(d["author_id"])) for d in docs]

    return MemoryListResponse(items=items, total=total, page=page, page_size=page_size)


async def delete_memory(memory_id: str, user_id: str, is_admin: bool = False) -> None:
    db = get_database()
    if not ObjectId.is_valid(memory_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souvenir introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(memory_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souvenir introuvable")
    if doc["author_id"] != user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres souvenirs")
    await db[COLLECTION].delete_one({"_id": ObjectId(memory_id)})


async def moderate_memory(memory_id: str, data: ModerateMemoryRequest) -> MemoryResponse:
    db = get_database()
    if not ObjectId.is_valid(memory_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souvenir introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(memory_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souvenir introuvable")
    await db[COLLECTION].update_one({"_id": ObjectId(memory_id)}, {"$set": {"status": data.status.value}})
    doc["status"] = data.status.value
    author = await db[USERS_COLLECTION].find_one({"_id": ObjectId(doc["author_id"])}) if ObjectId.is_valid(doc["author_id"]) else None
    return _to_response(doc, author)
