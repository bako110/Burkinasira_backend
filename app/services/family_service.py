from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.family import FamilyServiceType, FamilyServiceStatus
from app.schemas.family import (
    CreateFamilyServiceRequest,
    UpdateFamilyServiceRequest,
    FamilyServiceSummary,
    FamilyServiceDetail,
    FamilyServiceListResponse,
    BookChildcareRequest,
    ChildcareBookingResponse,
)

COLLECTION = "family_services"
CHILDCARE_BOOKINGS_COLLECTION = "childcare_bookings"


def _to_summary(doc: dict) -> FamilyServiceSummary:
    return FamilyServiceSummary(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc["type"],
        region=doc["region"],
        city=doc.get("city"),
        location=doc["location"],
        is_family_friendly=doc.get("is_family_friendly", True),
    )


def _to_detail(doc: dict) -> FamilyServiceDetail:
    return FamilyServiceDetail(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc["type"],
        description=doc.get("description"),
        region=doc["region"],
        city=doc.get("city"),
        location=doc["location"],
        address=doc.get("address"),
        is_family_friendly=doc.get("is_family_friendly", True),
        is_verified_provider=doc.get("is_verified_provider", False),
        contact_phone=doc.get("contact_phone"),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_family_service(data: CreateFamilyServiceRequest) -> FamilyServiceDetail:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["is_verified_provider"] = False
    doc["status"] = FamilyServiceStatus.PUBLISHED.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_family_services(
    type: Optional[FamilyServiceType] = None,
    region: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> FamilyServiceListResponse:
    db = get_database()
    query: dict = {"status": FamilyServiceStatus.PUBLISHED.value, "is_family_friendly": True}
    if type:
        query["type"] = type.value if isinstance(type, FamilyServiceType) else type
    if region:
        query["region"] = region
    if q:
        query["name"] = {"$regex": q, "$options": "i"}

    total = await db[COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    docs = await db[COLLECTION].find(query).skip(skip).limit(page_size).to_list(length=page_size)

    return FamilyServiceListResponse(
        items=[_to_summary(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_family_service(service_id: str) -> FamilyServiceDetail:
    db = get_database()
    if not ObjectId.is_valid(service_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(service_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")
    return _to_detail(doc)


async def update_family_service(service_id: str, data: UpdateFamilyServiceRequest) -> FamilyServiceDetail:
    db = get_database()
    if not ObjectId.is_valid(service_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[COLLECTION].update_one({"_id": ObjectId(service_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")
    return await get_family_service(service_id)


async def delete_family_service(service_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(service_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")
    result = await db[COLLECTION].delete_one({"_id": ObjectId(service_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")


# --- Réservation de garde d'enfants ---

def _booking_to_response(doc: dict) -> ChildcareBookingResponse:
    return ChildcareBookingResponse(
        id=str(doc["_id"]),
        service_id=doc["service_id"],
        parent_id=doc["parent_id"],
        requested_date=doc["requested_date"],
        notes=doc.get("notes"),
        status=doc["status"],
        created_at=doc["created_at"],
    )


async def book_childcare(data: BookChildcareRequest, parent_id: str) -> ChildcareBookingResponse:
    service = await get_family_service(data.service_id)
    if service.type != "garde_enfants":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce service n'est pas un service de garde d'enfants")

    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["parent_id"] = parent_id
    doc["status"] = "requested"
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[CHILDCARE_BOOKINGS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _booking_to_response(doc)


async def list_my_childcare_bookings(parent_id: str) -> list:
    db = get_database()
    docs = await db[CHILDCARE_BOOKINGS_COLLECTION].find({"parent_id": parent_id}).sort("created_at", -1).to_list(length=None)
    return [_booking_to_response(d) for d in docs]
