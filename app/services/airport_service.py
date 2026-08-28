from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.airport import AirportInfoCategory
from app.schemas.airport import (
    CreateAirportRequest,
    UpdateAirportRequest,
    AirportResponse,
    CreateAirportInfoRequest,
    UpdateAirportInfoRequest,
    AirportInfoResponse,
    CreateBorderCrossingRequest,
    UpdateBorderCrossingRequest,
    BorderCrossingResponse,
)

AIRPORTS_COLLECTION = "airports"
AIRPORT_INFO_COLLECTION = "airport_info"
BORDERS_COLLECTION = "border_crossings"


# --- Aéroports ---

def _airport_to_response(doc: dict) -> AirportResponse:
    return AirportResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        iata_code=doc.get("iata_code"),
        city=doc["city"],
        region=doc["region"],
        location=doc["location"],
        description=doc.get("description"),
    )


async def create_airport(data: CreateAirportRequest) -> AirportResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[AIRPORTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _airport_to_response(doc)


async def list_airports() -> list:
    db = get_database()
    docs = await db[AIRPORTS_COLLECTION].find({}).to_list(length=None)
    return [_airport_to_response(d) for d in docs]


async def get_airport(airport_id: str) -> AirportResponse:
    db = get_database()
    if not ObjectId.is_valid(airport_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aéroport introuvable")
    doc = await db[AIRPORTS_COLLECTION].find_one({"_id": ObjectId(airport_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aéroport introuvable")
    return _airport_to_response(doc)


async def update_airport(airport_id: str, data: UpdateAirportRequest) -> AirportResponse:
    db = get_database()
    if not ObjectId.is_valid(airport_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aéroport introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[AIRPORTS_COLLECTION].update_one({"_id": ObjectId(airport_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aéroport introuvable")
    return await get_airport(airport_id)


async def delete_airport(airport_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(airport_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aéroport introuvable")
    result = await db[AIRPORTS_COLLECTION].delete_one({"_id": ObjectId(airport_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aéroport introuvable")


# --- Informations aéroport ---

def _info_to_response(doc: dict) -> AirportInfoResponse:
    return AirportInfoResponse(
        id=str(doc["_id"]),
        airport_id=doc["airport_id"],
        category=doc["category"],
        title=doc["title"],
        content=doc["content"],
        updated_at=doc["updated_at"],
    )


async def add_airport_info(airport_id: str, data: CreateAirportInfoRequest) -> AirportInfoResponse:
    await get_airport(airport_id)  # 404 si inexistant
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["airport_id"] = airport_id
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[AIRPORT_INFO_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _info_to_response(doc)


async def list_airport_info(airport_id: str, category: Optional[AirportInfoCategory] = None) -> list:
    db = get_database()
    query: dict = {"airport_id": airport_id}
    if category:
        query["category"] = category.value if isinstance(category, AirportInfoCategory) else category
    docs = await db[AIRPORT_INFO_COLLECTION].find(query).to_list(length=None)
    return [_info_to_response(d) for d in docs]


async def update_airport_info(info_id: str, data: UpdateAirportInfoRequest) -> AirportInfoResponse:
    db = get_database()
    if not ObjectId.is_valid(info_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[AIRPORT_INFO_COLLECTION].update_one({"_id": ObjectId(info_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information introuvable")
    doc = await db[AIRPORT_INFO_COLLECTION].find_one({"_id": ObjectId(info_id)})
    return _info_to_response(doc)


async def delete_airport_info(info_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(info_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information introuvable")
    result = await db[AIRPORT_INFO_COLLECTION].delete_one({"_id": ObjectId(info_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information introuvable")


# --- Frontières ---

def _border_to_response(doc: dict) -> BorderCrossingResponse:
    return BorderCrossingResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        neighboring_country=doc["neighboring_country"],
        region=doc["region"],
        location=doc.get("location"),
        notes=doc.get("notes"),
    )


async def create_border_crossing(data: CreateBorderCrossingRequest) -> BorderCrossingResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[BORDERS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _border_to_response(doc)


async def list_border_crossings(region: Optional[str] = None) -> list:
    db = get_database()
    query: dict = {}
    if region:
        query["region"] = region
    docs = await db[BORDERS_COLLECTION].find(query).to_list(length=None)
    return [_border_to_response(d) for d in docs]


async def get_border_crossing(border_id: str) -> BorderCrossingResponse:
    db = get_database()
    if not ObjectId.is_valid(border_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontière introuvable")
    doc = await db[BORDERS_COLLECTION].find_one({"_id": ObjectId(border_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontière introuvable")
    return _border_to_response(doc)


async def update_border_crossing(border_id: str, data: UpdateBorderCrossingRequest) -> BorderCrossingResponse:
    db = get_database()
    if not ObjectId.is_valid(border_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontière introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[BORDERS_COLLECTION].update_one({"_id": ObjectId(border_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontière introuvable")
    return await get_border_crossing(border_id)


async def delete_border_crossing(border_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(border_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontière introuvable")
    result = await db[BORDERS_COLLECTION].delete_one({"_id": ObjectId(border_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontière introuvable")
