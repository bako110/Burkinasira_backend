from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.verified import VerificationStatus, DisputeStatus
from app.schemas.verified import (
    SubmitVerificationRequest,
    ReviewVerificationRequest,
    VerificationRequestResponse,
    VerificationRequestAdminSummary,
    PendingEstablishmentSummary,
    CreateDisputeRequest,
    ResolveDisputeRequest,
    DisputeResponse,
    ReportSuspiciousRequest,
    SuspiciousReportResponse,
)

VERIFICATION_COLLECTION = "verification_requests"
DISPUTES_COLLECTION = "disputes"
SUSPICIOUS_REPORTS_COLLECTION = "suspicious_activity_reports"


# --- Vérification d'identité/documents ---

def _verification_to_response(doc: dict) -> VerificationRequestResponse:
    return VerificationRequestResponse(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        document_type=doc["document_type"],
        document_url=doc["document_url"],
        status=doc.get("status", VerificationStatus.PENDING.value),
        review_notes=doc.get("review_notes"),
        created_at=doc["created_at"],
    )


async def submit_verification(data: SubmitVerificationRequest, user_id: str) -> VerificationRequestResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["user_id"] = user_id
    doc["status"] = VerificationStatus.PENDING.value
    doc["reviewed_by"] = None
    doc["review_notes"] = None
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[VERIFICATION_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _verification_to_response(doc)


async def list_my_verifications(user_id: str) -> list:
    db = get_database()
    docs = await db[VERIFICATION_COLLECTION].find({"user_id": user_id}).sort("created_at", -1).to_list(length=None)
    return [_verification_to_response(d) for d in docs]


async def _find_pending_establishments(db, owner_id: str) -> list:
    """Aperçu des établissements en brouillon/attente déjà soumis par ce compte,
    pour aider l'admin à évaluer la demande sans changer d'écran."""
    from app.models.hotel import HotelStatus
    from app.models.cuisine import CuisineStatus
    from app.models.mobility import TransportProviderStatus
    from app.models.artisan import ArtisanStatus

    summaries = []
    async for doc in db["hotels"].find({"owner_id": owner_id, "status": HotelStatus.DRAFT.value}, {"name": 1}):
        summaries.append(PendingEstablishmentSummary(kind="hotel", name=doc["name"]))
    async for doc in db["restaurants"].find({"owner_id": owner_id, "status": CuisineStatus.DRAFT.value}, {"name": 1}):
        summaries.append(PendingEstablishmentSummary(kind="restaurant", name=doc["name"]))
    async for doc in db["transport_providers"].find(
        {"owner_id": owner_id, "status": TransportProviderStatus.PENDING.value}, {"name": 1}
    ):
        summaries.append(PendingEstablishmentSummary(kind="transport", name=doc["name"]))
    async for doc in db["artisans"].find(
        {"user_id": owner_id, "status": ArtisanStatus.PENDING.value}, {"display_name": 1}
    ):
        summaries.append(PendingEstablishmentSummary(kind="artisan", name=doc["display_name"]))
    return summaries


async def list_pending_verifications() -> list:
    db = get_database()
    docs = await db[VERIFICATION_COLLECTION].find({"status": VerificationStatus.PENDING.value}).to_list(length=None)

    summaries = []
    for doc in docs:
        user = None
        if ObjectId.is_valid(doc["user_id"]):
            user = await db["users"].find_one({"_id": ObjectId(doc["user_id"])})
        pending_establishments = await _find_pending_establishments(db, doc["user_id"])
        summaries.append(
            VerificationRequestAdminSummary(
                id=str(doc["_id"]),
                user_id=doc["user_id"],
                user_full_name=user.get("full_name", "Utilisateur") if user else "Utilisateur introuvable",
                user_email=user.get("email", "") if user else "",
                user_role=user.get("role", "") if user else "",
                document_type=doc["document_type"],
                document_url=doc["document_url"],
                status=doc.get("status", VerificationStatus.PENDING.value),
                review_notes=doc.get("review_notes"),
                created_at=doc["created_at"],
                pending_establishments=pending_establishments,
            )
        )
    return summaries


async def review_verification(request_id: str, data: ReviewVerificationRequest, reviewer_id: str) -> VerificationRequestResponse:
    db = get_database()
    if not ObjectId.is_valid(request_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable")

    existing = await db[VERIFICATION_COLLECTION].find_one({"_id": ObjectId(request_id)})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable")

    await db[VERIFICATION_COLLECTION].update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {
            "status": data.status.value,
            "review_notes": data.review_notes,
            "reviewed_by": reviewer_id,
            "updated_at": datetime.utcnow(),
        }},
    )

    if data.status == VerificationStatus.ACTIVE and ObjectId.is_valid(existing["user_id"]):
        user_id = existing["user_id"]
        await db["users"].update_one({"_id": ObjectId(user_id)}, {"$set": {"is_verified": True}})
        await _publish_pending_establishments(db, user_id)

    doc = await db[VERIFICATION_COLLECTION].find_one({"_id": ObjectId(request_id)})
    return _verification_to_response(doc)


async def _publish_pending_establishments(db, owner_id: str) -> None:
    """Une fois le compte provider approuvé, publie automatiquement les
    établissements qu'il avait déjà créés en brouillon/attente."""
    from app.models.hotel import HotelStatus
    from app.models.cuisine import CuisineStatus
    from app.models.mobility import TransportProviderStatus
    from app.models.artisan import ArtisanStatus

    now = datetime.utcnow()
    await db["hotels"].update_many(
        {"owner_id": owner_id, "status": HotelStatus.DRAFT.value},
        {"$set": {"status": HotelStatus.PUBLISHED.value, "updated_at": now}},
    )
    await db["restaurants"].update_many(
        {"owner_id": owner_id, "status": CuisineStatus.DRAFT.value},
        {"$set": {"status": CuisineStatus.PUBLISHED.value, "updated_at": now}},
    )
    await db["transport_providers"].update_many(
        {"owner_id": owner_id, "status": TransportProviderStatus.PENDING.value},
        {"$set": {"status": TransportProviderStatus.ACTIVE.value, "updated_at": now}},
    )
    await db["artisans"].update_many(
        {"user_id": owner_id, "status": ArtisanStatus.PENDING.value},
        {"$set": {"status": ArtisanStatus.ACTIVE.value, "updated_at": now}},
    )


# --- Litiges ---

def _dispute_to_response(doc: dict) -> DisputeResponse:
    return DisputeResponse(
        id=str(doc["_id"]),
        complainant_id=doc["complainant_id"],
        against_user_id=doc.get("against_user_id"),
        subject=doc["subject"],
        description=doc["description"],
        related_booking_id=doc.get("related_booking_id"),
        status=doc.get("status", DisputeStatus.OPEN.value),
        resolution_notes=doc.get("resolution_notes"),
        created_at=doc["created_at"],
    )


async def open_dispute(data: CreateDisputeRequest, complainant_id: str) -> DisputeResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["complainant_id"] = complainant_id
    doc["status"] = DisputeStatus.OPEN.value
    doc["resolution_notes"] = None
    doc["resolved_by"] = None
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[DISPUTES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _dispute_to_response(doc)


async def list_my_disputes(complainant_id: str) -> list:
    db = get_database()
    docs = await db[DISPUTES_COLLECTION].find({"complainant_id": complainant_id}).sort("created_at", -1).to_list(length=None)
    return [_dispute_to_response(d) for d in docs]


async def list_all_disputes(status_filter: Optional[DisputeStatus] = None) -> list:
    db = get_database()
    query: dict = {}
    if status_filter:
        query["status"] = status_filter.value if isinstance(status_filter, DisputeStatus) else status_filter
    docs = await db[DISPUTES_COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_dispute_to_response(d) for d in docs]


async def resolve_dispute(dispute_id: str, data: ResolveDisputeRequest, resolver_id: str) -> DisputeResponse:
    db = get_database()
    if not ObjectId.is_valid(dispute_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Litige introuvable")
    result = await db[DISPUTES_COLLECTION].update_one(
        {"_id": ObjectId(dispute_id)},
        {"$set": {
            "status": data.status.value,
            "resolution_notes": data.resolution_notes,
            "resolved_by": resolver_id,
            "updated_at": datetime.utcnow(),
        }},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Litige introuvable")
    doc = await db[DISPUTES_COLLECTION].find_one({"_id": ObjectId(dispute_id)})
    return _dispute_to_response(doc)


# --- Signalement de profil/contenu suspect ---

def _suspicious_to_response(doc: dict) -> SuspiciousReportResponse:
    return SuspiciousReportResponse(
        id=str(doc["_id"]),
        reporter_id=doc["reporter_id"],
        type=doc["type"],
        target_id=doc["target_id"],
        reason=doc["reason"],
        status=doc.get("status", DisputeStatus.OPEN.value),
        created_at=doc["created_at"],
    )


async def report_suspicious(data: ReportSuspiciousRequest, reporter_id: str) -> SuspiciousReportResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["reporter_id"] = reporter_id
    doc["status"] = DisputeStatus.OPEN.value
    doc["created_at"] = now
    result = await db[SUSPICIOUS_REPORTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _suspicious_to_response(doc)
