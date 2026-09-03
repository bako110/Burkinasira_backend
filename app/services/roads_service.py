from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.roads import RoadServiceType, RoadServiceStatus, BreakdownReportStatus
from app.schemas.roads import (
    CreateRoadServiceRequest,
    UpdateRoadServiceRequest,
    RoadServiceSummary,
    RoadServiceDetail,
    RoadServiceListResponse,
    ReportBreakdownRequest,
    BreakdownReportResponse,
)

COLLECTION = "road_services"
BREAKDOWNS_COLLECTION = "breakdown_reports"


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def _to_summary(doc: dict) -> RoadServiceSummary:
    return RoadServiceSummary(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc["type"],
        region=doc["region"],
        city=doc.get("city"),
        location=doc["location"],
        offers_24h=doc.get("offers_24h", False),
        contact_phone=doc.get("contact_phone"),
    )


def _to_detail(doc: dict) -> RoadServiceDetail:
    return RoadServiceDetail(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc["type"],
        description=doc.get("description"),
        region=doc["region"],
        city=doc.get("city"),
        location=doc["location"],
        address=doc.get("address"),
        opening_hours=doc.get("opening_hours", []),
        offers_24h=doc.get("offers_24h", False),
        contact_phone=doc.get("contact_phone"),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_road_service(data: CreateRoadServiceRequest) -> RoadServiceDetail:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["status"] = RoadServiceStatus.PUBLISHED.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_road_services(
    type: Optional[RoadServiceType] = None,
    region: Optional[str] = None,
    q: Optional[str] = None,
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    page: int = 1,
    page_size: int = 20,
) -> RoadServiceListResponse:
    db = get_database()
    query: dict = {"status": RoadServiceStatus.PUBLISHED.value}
    if type:
        query["type"] = type.value if isinstance(type, RoadServiceType) else type
    if region:
        query["region"] = region
    if q:
        query["name"] = {"$regex": q, "$options": "i"}

    all_docs = await db[COLLECTION].find(query).to_list(length=None)

    if near_lat is not None and near_lng is not None:
        all_docs.sort(
            key=lambda d: _haversine_km(near_lat, near_lng, d["location"]["latitude"], d["location"]["longitude"])
        )
        if radius_km is not None:
            all_docs = [
                d for d in all_docs
                if _haversine_km(near_lat, near_lng, d["location"]["latitude"], d["location"]["longitude"]) <= radius_km
            ]

    total = len(all_docs)
    start = (page - 1) * page_size
    page_docs = all_docs[start:start + page_size]

    return RoadServiceListResponse(
        items=[_to_summary(d) for d in page_docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_road_service(service_id: str) -> RoadServiceDetail:
    db = get_database()
    if not ObjectId.is_valid(service_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(service_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")
    return _to_detail(doc)


async def update_road_service(service_id: str, data: UpdateRoadServiceRequest) -> RoadServiceDetail:
    db = get_database()
    if not ObjectId.is_valid(service_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[COLLECTION].update_one({"_id": ObjectId(service_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")
    return await get_road_service(service_id)


async def delete_road_service(service_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(service_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")
    result = await db[COLLECTION].delete_one({"_id": ObjectId(service_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")


# --- Signalement de panne ---

def _breakdown_to_response(doc: dict) -> BreakdownReportResponse:
    return BreakdownReportResponse(
        id=str(doc["_id"]),
        reporter_id=doc["reporter_id"],
        location=doc["location"],
        description=doc.get("description"),
        assigned_service_id=doc.get("assigned_service_id"),
        status=doc.get("status", BreakdownReportStatus.OPEN.value),
        created_at=doc["created_at"],
    )


async def report_breakdown(data: ReportBreakdownRequest, reporter_id: str) -> BreakdownReportResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["reporter_id"] = reporter_id
    doc["assigned_service_id"] = None
    doc["status"] = BreakdownReportStatus.OPEN.value
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[BREAKDOWNS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _breakdown_to_response(doc)


async def list_my_breakdowns(reporter_id: str) -> list:
    db = get_database()
    docs = await db[BREAKDOWNS_COLLECTION].find({"reporter_id": reporter_id}).sort("created_at", -1).to_list(length=None)
    return [_breakdown_to_response(d) for d in docs]


async def assign_breakdown(report_id: str, service_id: str) -> BreakdownReportResponse:
    await get_road_service(service_id)  # 404 si inexistant
    db = get_database()
    if not ObjectId.is_valid(report_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signalement introuvable")
    result = await db[BREAKDOWNS_COLLECTION].update_one(
        {"_id": ObjectId(report_id)},
        {"$set": {"assigned_service_id": service_id, "status": BreakdownReportStatus.ASSIGNED.value, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signalement introuvable")
    doc = await db[BREAKDOWNS_COLLECTION].find_one({"_id": ObjectId(report_id)})
    return _breakdown_to_response(doc)
