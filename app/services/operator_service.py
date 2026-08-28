from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.operator import OperatorCategory, OperatorApplicationStatus
from app.schemas.operator import (
    CreateOperatorApplicationRequest,
    ReviewOperatorApplicationRequest,
    OperatorApplicationResponse,
)

COLLECTION = "operator_applications"


def _to_response(doc: dict) -> OperatorApplicationResponse:
    return OperatorApplicationResponse(
        id=str(doc["_id"]),
        applicant_id=doc["applicant_id"],
        category=doc["category"],
        business_name=doc["business_name"],
        documents=doc.get("documents", []),
        notes=doc.get("notes"),
        status=doc.get("status", OperatorApplicationStatus.SUBMITTED.value),
        reviewed_by=doc.get("reviewed_by"),
        review_notes=doc.get("review_notes"),
        created_at=doc["created_at"],
    )


async def submit_application(data: CreateOperatorApplicationRequest, applicant_id: str) -> OperatorApplicationResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["applicant_id"] = applicant_id
    doc["status"] = OperatorApplicationStatus.SUBMITTED.value
    doc["reviewed_by"] = None
    doc["review_notes"] = None
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_response(doc)


async def list_my_applications(applicant_id: str) -> list:
    db = get_database()
    docs = await db[COLLECTION].find({"applicant_id": applicant_id}).sort("created_at", -1).to_list(length=None)
    return [_to_response(d) for d in docs]


async def list_applications(status_filter: Optional[OperatorApplicationStatus] = None) -> list:
    db = get_database()
    query: dict = {}
    if status_filter:
        query["status"] = status_filter.value if isinstance(status_filter, OperatorApplicationStatus) else status_filter
    docs = await db[COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_to_response(d) for d in docs]


async def get_application(application_id: str, current_user_id: str, is_admin: bool) -> OperatorApplicationResponse:
    db = get_database()
    if not ObjectId.is_valid(application_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(application_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    if doc["applicant_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    return _to_response(doc)


async def review_application(application_id: str, data: ReviewOperatorApplicationRequest, reviewer_id: str) -> OperatorApplicationResponse:
    """(Admin) Valider ou suspendre un prestataire."""
    db = get_database()
    if not ObjectId.is_valid(application_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    result = await db[COLLECTION].update_one(
        {"_id": ObjectId(application_id)},
        {"$set": {
            "status": data.status.value,
            "review_notes": data.review_notes,
            "reviewed_by": reviewer_id,
            "updated_at": datetime.utcnow(),
        }},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(application_id)})
    return _to_response(doc)
