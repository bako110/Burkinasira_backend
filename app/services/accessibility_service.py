from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.accessibility import AccessibilityReportStatus
from app.schemas.accessibility import (
    ReportObstacleRequest,
    ObstacleReportResponse,
    ModerateObstacleRequest,
)

COLLECTION = "accessibility_obstacle_reports"


def _to_response(doc: dict) -> ObstacleReportResponse:
    return ObstacleReportResponse(
        id=str(doc["_id"]),
        reporter_id=doc["reporter_id"],
        location=doc["location"],
        description=doc["description"],
        related_destination_id=doc.get("related_destination_id"),
        status=doc.get("status", AccessibilityReportStatus.REPORTED.value),
        created_at=doc["created_at"],
    )


async def report_obstacle(data: ReportObstacleRequest, reporter_id: str) -> ObstacleReportResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["reporter_id"] = reporter_id
    doc["status"] = AccessibilityReportStatus.REPORTED.value
    doc["moderated_by"] = None
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_response(doc)


async def list_obstacle_reports(status_filter: Optional[AccessibilityReportStatus] = None) -> list:
    db = get_database()
    query: dict = {}
    if status_filter:
        query["status"] = status_filter.value if isinstance(status_filter, AccessibilityReportStatus) else status_filter
    docs = await db[COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_to_response(d) for d in docs]


async def moderate_obstacle_report(report_id: str, data: ModerateObstacleRequest, moderator_id: str) -> ObstacleReportResponse:
    db = get_database()
    if not ObjectId.is_valid(report_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signalement introuvable")
    result = await db[COLLECTION].update_one(
        {"_id": ObjectId(report_id)},
        {"$set": {"status": data.status.value, "moderated_by": moderator_id, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signalement introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(report_id)})
    return _to_response(doc)
