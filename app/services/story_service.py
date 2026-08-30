from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.story import CultureContentType
from app.schemas.story import (
    CreateCultureContentRequest,
    UpdateCultureContentRequest,
    CultureContentSummary,
    CultureContentDetail,
    CultureContentListResponse,
    CreateCulturalRouteRequest,
    UpdateCulturalRouteRequest,
    CulturalRouteResponse,
)

CONTENT_COLLECTION = "culture_contents"
ROUTES_COLLECTION = "cultural_routes"


def _content_to_summary(doc: dict) -> CultureContentSummary:
    return CultureContentSummary(
        id=str(doc["_id"]),
        title=doc["title"],
        type=doc["type"],
        media_type=doc.get("media_type", "texte"),
        summary=doc.get("summary"),
        cover_photo=doc.get("cover_photo"),
        region=doc.get("region"),
        province=doc.get("province"),
    )


def _content_to_detail(doc: dict) -> CultureContentDetail:
    return CultureContentDetail(
        id=str(doc["_id"]),
        title=doc["title"],
        type=doc["type"],
        media_type=doc.get("media_type", "texte"),
        summary=doc.get("summary"),
        content=doc.get("content"),
        media_url=doc.get("media_url"),
        cover_photo=doc.get("cover_photo"),
        region=doc.get("region"),
        province=doc.get("province"),
        related_destination_ids=doc.get("related_destination_ids", []),
        author=doc.get("author"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_content(data: CreateCultureContentRequest, created_by: str) -> CultureContentDetail:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["created_by"] = created_by
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[CONTENT_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _content_to_detail(doc)


async def list_content(
    type: Optional[CultureContentType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> CultureContentListResponse:
    db = get_database()
    query: dict = {}
    if type:
        query["type"] = type.value if isinstance(type, CultureContentType) else type
    if region:
        query["region"] = region
    if province:
        query["province"] = province
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"summary": {"$regex": q, "$options": "i"}},
        ]

    total = await db[CONTENT_COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    docs = await db[CONTENT_COLLECTION].find(query).skip(skip).limit(page_size).to_list(length=page_size)

    return CultureContentListResponse(
        items=[_content_to_summary(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_content(content_id: str) -> CultureContentDetail:
    db = get_database()
    if not ObjectId.is_valid(content_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu culturel introuvable")
    doc = await db[CONTENT_COLLECTION].find_one({"_id": ObjectId(content_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu culturel introuvable")
    return _content_to_detail(doc)


async def update_content(content_id: str, data: UpdateCultureContentRequest) -> CultureContentDetail:
    db = get_database()
    if not ObjectId.is_valid(content_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu culturel introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[CONTENT_COLLECTION].update_one({"_id": ObjectId(content_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu culturel introuvable")
    return await get_content(content_id)


async def delete_content(content_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(content_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu culturel introuvable")
    result = await db[CONTENT_COLLECTION].delete_one({"_id": ObjectId(content_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu culturel introuvable")


# --- Parcours culturels ---

def _route_to_response(doc: dict) -> CulturalRouteResponse:
    return CulturalRouteResponse(
        id=str(doc["_id"]),
        title=doc["title"],
        description=doc.get("description"),
        region=doc.get("region"),
        province=doc.get("province"),
        step_destination_ids=doc.get("step_destination_ids", []),
        step_content_ids=doc.get("step_content_ids", []),
        created_at=doc["created_at"],
    )


async def create_route(data: CreateCulturalRouteRequest, created_by: str) -> CulturalRouteResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["created_by"] = created_by
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[ROUTES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _route_to_response(doc)


async def list_routes(region: Optional[str] = None, province: Optional[str] = None) -> list:
    db = get_database()
    query: dict = {}
    if region:
        query["region"] = region
    if province:
        query["province"] = province
    docs = await db[ROUTES_COLLECTION].find(query).to_list(length=None)
    return [_route_to_response(d) for d in docs]


async def get_route(route_id: str) -> CulturalRouteResponse:
    db = get_database()
    if not ObjectId.is_valid(route_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcours culturel introuvable")
    doc = await db[ROUTES_COLLECTION].find_one({"_id": ObjectId(route_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcours culturel introuvable")
    return _route_to_response(doc)


async def update_route(route_id: str, data: UpdateCulturalRouteRequest) -> CulturalRouteResponse:
    db = get_database()
    if not ObjectId.is_valid(route_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcours culturel introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[ROUTES_COLLECTION].update_one({"_id": ObjectId(route_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcours culturel introuvable")
    return await get_route(route_id)


async def delete_route(route_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(route_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcours culturel introuvable")
    result = await db[ROUTES_COLLECTION].delete_one({"_id": ObjectId(route_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcours culturel introuvable")
