from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.data_quality import DataErrorReportStatus
from app.schemas.data_quality import (
    ReportDataErrorRequest,
    DataErrorReportResponse,
    ModerateDataErrorRequest,
    DuplicateCandidateResponse,
    ResolveDuplicateRequest,
    DataChangeLogResponse,
)

ERROR_REPORTS_COLLECTION = "data_error_reports"
CHANGE_LOG_COLLECTION = "data_change_log"
DUPLICATES_COLLECTION = "duplicate_candidates"

ITEM_TYPE_COLLECTIONS = {
    "destination": "destinations",
    "hotel": "hotels",
    "restaurant": "restaurants",
    "health_facility": "health_facilities",
    "road_service": "road_services",
    "money_service": "money_service_points",
}

SIMILARITY_THRESHOLD = 0.85


# --- Signalement d'erreurs ---

def _report_to_response(doc: dict) -> DataErrorReportResponse:
    return DataErrorReportResponse(
        id=str(doc["_id"]),
        reporter_id=doc["reporter_id"],
        item_type=doc["item_type"],
        item_id=doc["item_id"],
        description=doc["description"],
        status=doc.get("status", DataErrorReportStatus.REPORTED.value),
        created_at=doc["created_at"],
    )


async def report_error(data: ReportDataErrorRequest, reporter_id: str) -> DataErrorReportResponse:
    db = get_database()
    doc = data.model_dump()
    doc["reporter_id"] = reporter_id
    doc["status"] = DataErrorReportStatus.REPORTED.value
    doc["reviewed_by"] = None
    doc["created_at"] = datetime.utcnow()
    result = await db[ERROR_REPORTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _report_to_response(doc)


async def list_error_reports(status_filter: Optional[DataErrorReportStatus] = None) -> list:
    db = get_database()
    query: dict = {}
    if status_filter:
        query["status"] = status_filter.value if isinstance(status_filter, DataErrorReportStatus) else status_filter
    docs = await db[ERROR_REPORTS_COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_report_to_response(d) for d in docs]


async def moderate_error_report(report_id: str, data: ModerateDataErrorRequest, reviewer_id: str) -> DataErrorReportResponse:
    db = get_database()
    if not ObjectId.is_valid(report_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signalement introuvable")
    result = await db[ERROR_REPORTS_COLLECTION].update_one(
        {"_id": ObjectId(report_id)},
        {"$set": {"status": data.status.value, "reviewed_by": reviewer_id}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signalement introuvable")
    doc = await db[ERROR_REPORTS_COLLECTION].find_one({"_id": ObjectId(report_id)})
    return _report_to_response(doc)


# --- Détection de doublons ---

def _duplicate_to_response(doc: dict) -> DuplicateCandidateResponse:
    return DuplicateCandidateResponse(
        id=str(doc["_id"]),
        item_type=doc["item_type"],
        item_id_a=doc["item_id_a"],
        item_id_b=doc["item_id_b"],
        similarity_score=doc["similarity_score"],
        resolved=doc.get("resolved", False),
    )


async def detect_duplicates(item_type: str) -> list:
    """(Admin) Détecter les doublons potentiels par similarité de nom sur un type de fiche."""
    collection_name = ITEM_TYPE_COLLECTIONS.get(item_type)
    if not collection_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Type de fiche non supporté: {item_type}")

    db = get_database()
    docs = await db[collection_name].find({}, {"name": 1}).to_list(length=None)

    found = []
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            name_a, name_b = docs[i].get("name", ""), docs[j].get("name", "")
            score = SequenceMatcher(None, name_a.lower(), name_b.lower()).ratio()
            if score >= SIMILARITY_THRESHOLD:
                dup_doc = {
                    "item_type": item_type,
                    "item_id_a": str(docs[i]["_id"]),
                    "item_id_b": str(docs[j]["_id"]),
                    "similarity_score": round(score, 3),
                    "resolved": False,
                    "created_at": datetime.utcnow(),
                }
                await db[DUPLICATES_COLLECTION].update_one(
                    {"item_type": item_type, "item_id_a": dup_doc["item_id_a"], "item_id_b": dup_doc["item_id_b"]},
                    {"$setOnInsert": dup_doc},
                    upsert=True,
                )
                found.append(dup_doc)

    return found


async def list_duplicates(item_type: Optional[str] = None, resolved: Optional[bool] = None) -> list:
    db = get_database()
    query: dict = {}
    if item_type:
        query["item_type"] = item_type
    if resolved is not None:
        query["resolved"] = resolved
    docs = await db[DUPLICATES_COLLECTION].find(query).to_list(length=None)
    return [_duplicate_to_response(d) for d in docs]


async def resolve_duplicate(duplicate_id: str, data: ResolveDuplicateRequest) -> DuplicateCandidateResponse:
    db = get_database()
    if not ObjectId.is_valid(duplicate_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doublon introuvable")
    result = await db[DUPLICATES_COLLECTION].update_one(
        {"_id": ObjectId(duplicate_id)}, {"$set": {"resolved": data.resolved}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doublon introuvable")
    doc = await db[DUPLICATES_COLLECTION].find_one({"_id": ObjectId(duplicate_id)})
    return _duplicate_to_response(doc)


# --- Historique des modifications ---

async def log_change(item_type: str, item_id: str, changed_by: str, change_summary: str) -> None:
    db = get_database()
    await db[CHANGE_LOG_COLLECTION].insert_one({
        "item_type": item_type,
        "item_id": item_id,
        "changed_by": changed_by,
        "change_summary": change_summary,
        "created_at": datetime.utcnow(),
    })


async def get_change_history(item_type: str, item_id: str) -> list:
    db = get_database()
    docs = await db[CHANGE_LOG_COLLECTION].find(
        {"item_type": item_type, "item_id": item_id}
    ).sort("created_at", -1).to_list(length=None)
    return [
        DataChangeLogResponse(
            id=str(d["_id"]), item_type=d["item_type"], item_id=d["item_id"],
            changed_by=d["changed_by"], change_summary=d["change_summary"], created_at=d["created_at"],
        )
        for d in docs
    ]
