from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.tourist_info import TravelInfoCategory
from app.schemas.tourist_info import (
    CreateTravelInfoRequest,
    UpdateTravelInfoRequest,
    TravelInfoResponse,
    CreateDiplomaticContactRequest,
    UpdateDiplomaticContactRequest,
    DiplomaticContactResponse,
)

INFO_COLLECTION = "travel_info"
DIPLOMATIC_COLLECTION = "diplomatic_contacts"


def _info_to_response(doc: dict) -> TravelInfoResponse:
    return TravelInfoResponse(
        id=str(doc["_id"]),
        category=doc["category"],
        title=doc["title"],
        content=doc["content"],
        source_type=doc.get("source_type", "officiel"),
        official_url=doc.get("official_url"),
        country_scope=doc.get("country_scope", "Burkina Faso"),
        updated_at=doc["updated_at"],
    )


async def create_travel_info(data: CreateTravelInfoRequest) -> TravelInfoResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[INFO_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _info_to_response(doc)


async def list_travel_info(category: Optional[TravelInfoCategory] = None) -> list:
    db = get_database()
    query: dict = {}
    if category:
        query["category"] = category.value if isinstance(category, TravelInfoCategory) else category
    docs = await db[INFO_COLLECTION].find(query).to_list(length=None)
    return [_info_to_response(d) for d in docs]


async def get_travel_info(info_id: str) -> TravelInfoResponse:
    db = get_database()
    if not ObjectId.is_valid(info_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information introuvable")
    doc = await db[INFO_COLLECTION].find_one({"_id": ObjectId(info_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information introuvable")
    return _info_to_response(doc)


async def update_travel_info(info_id: str, data: UpdateTravelInfoRequest) -> TravelInfoResponse:
    db = get_database()
    if not ObjectId.is_valid(info_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[INFO_COLLECTION].update_one({"_id": ObjectId(info_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information introuvable")
    return await get_travel_info(info_id)


async def delete_travel_info(info_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(info_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information introuvable")
    result = await db[INFO_COLLECTION].delete_one({"_id": ObjectId(info_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information introuvable")


# --- Contacts diplomatiques ---

def _diplomatic_to_response(doc: dict) -> DiplomaticContactResponse:
    return DiplomaticContactResponse(
        id=str(doc["_id"]),
        country=doc["country"],
        type=doc.get("type", "ambassade"),
        address=doc.get("address"),
        city=doc.get("city"),
        phone=doc.get("phone"),
        email=doc.get("email"),
        website=doc.get("website"),
    )


async def create_diplomatic_contact(data: CreateDiplomaticContactRequest) -> DiplomaticContactResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[DIPLOMATIC_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _diplomatic_to_response(doc)


async def list_diplomatic_contacts(country: Optional[str] = None) -> list:
    db = get_database()
    query: dict = {}
    if country:
        query["country"] = country
    docs = await db[DIPLOMATIC_COLLECTION].find(query).to_list(length=None)
    return [_diplomatic_to_response(d) for d in docs]


async def update_diplomatic_contact(contact_id: str, data: UpdateDiplomaticContactRequest) -> DiplomaticContactResponse:
    db = get_database()
    if not ObjectId.is_valid(contact_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[DIPLOMATIC_COLLECTION].update_one({"_id": ObjectId(contact_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact introuvable")
    doc = await db[DIPLOMATIC_COLLECTION].find_one({"_id": ObjectId(contact_id)})
    return _diplomatic_to_response(doc)


async def delete_diplomatic_contact(contact_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(contact_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact introuvable")
    result = await db[DIPLOMATIC_COLLECTION].delete_one({"_id": ObjectId(contact_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact introuvable")
