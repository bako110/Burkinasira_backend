from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.privacy import ConsentType, SensitiveActionType
from app.schemas.privacy import (
    SetConsentRequest,
    ConsentResponse,
    DataExportResponse,
    CreateRetentionPolicyRequest,
    RetentionPolicyResponse,
)

CONSENTS_COLLECTION = "user_consents"
PRIVACY_LOG_COLLECTION = "privacy_action_log"
RETENTION_COLLECTION = "data_retention_policies"


async def log_privacy_action(user_id: str, action: SensitiveActionType, details: Optional[str] = None) -> None:
    db = get_database()
    await db[PRIVACY_LOG_COLLECTION].insert_one({
        "user_id": user_id,
        "action": action.value if isinstance(action, SensitiveActionType) else action,
        "details": details,
        "created_at": datetime.utcnow(),
    })


# --- Consentements ---

async def set_consent(data: SetConsentRequest, user_id: str) -> ConsentResponse:
    db = get_database()
    now = datetime.utcnow()
    await db[CONSENTS_COLLECTION].update_one(
        {"user_id": user_id, "consent_type": data.consent_type.value},
        {"$set": {"granted": data.granted, "updated_at": now}},
        upsert=True,
    )
    await log_privacy_action(user_id, SensitiveActionType.CONSENT_UPDATED, details=data.consent_type.value)
    return ConsentResponse(consent_type=data.consent_type, granted=data.granted, updated_at=now)


async def list_my_consents(user_id: str) -> list:
    db = get_database()
    docs = await db[CONSENTS_COLLECTION].find({"user_id": user_id}).to_list(length=None)
    existing_types = {d["consent_type"] for d in docs}

    results = [ConsentResponse(consent_type=d["consent_type"], granted=d["granted"], updated_at=d["updated_at"]) for d in docs]
    for c in ConsentType:
        if c.value not in existing_types:
            results.append(ConsentResponse(consent_type=c, granted=False, updated_at=datetime.utcnow()))
    return results


# --- Export de données personnelles ---

async def export_my_data(user_id: str) -> DataExportResponse:
    db = get_database()

    user_doc = await db["users"].find_one({"_id": ObjectId(user_id)}) if ObjectId.is_valid(user_id) else None
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    user_doc["_id"] = str(user_doc["_id"])
    user_doc.pop("hashed_password", None)

    bookings = await db["bookings"].find({"customer_id": user_id}).to_list(length=None)
    for b in bookings:
        b["_id"] = str(b["_id"])

    trips = await db["trips"].find({"owner_id": user_id}).to_list(length=None)
    for t in trips:
        t["_id"] = str(t["_id"])

    posts = await db["community_posts"].find({"author_id": user_id}).to_list(length=None)
    for p in posts:
        p["_id"] = str(p["_id"])

    await log_privacy_action(user_id, SensitiveActionType.DATA_EXPORT_REQUESTED)

    return DataExportResponse(
        user=user_doc, bookings=bookings, trips=trips, community_posts=posts,
        generated_at=datetime.utcnow(),
    )


# --- Politique de rétention ---

def _retention_to_response(doc: dict) -> RetentionPolicyResponse:
    return RetentionPolicyResponse(
        id=str(doc["_id"]),
        data_category=doc["data_category"],
        retention_days=doc["retention_days"],
        description=doc.get("description"),
        updated_at=doc["updated_at"],
    )


async def set_retention_policy(data: CreateRetentionPolicyRequest) -> RetentionPolicyResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["updated_at"] = now
    await db[RETENTION_COLLECTION].update_one(
        {"data_category": data.data_category}, {"$set": doc}, upsert=True,
    )
    result = await db[RETENTION_COLLECTION].find_one({"data_category": data.data_category})
    return _retention_to_response(result)


async def list_retention_policies() -> list:
    db = get_database()
    docs = await db[RETENTION_COLLECTION].find({}).to_list(length=None)
    return [_retention_to_response(d) for d in docs]


# --- Journal des actions sensibles ---

async def list_privacy_log(user_id: Optional[str] = None) -> list:
    db = get_database()
    query: dict = {"user_id": user_id} if user_id else {}
    docs = await db[PRIVACY_LOG_COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [
        {
            "id": str(d["_id"]), "user_id": d["user_id"], "action": d["action"],
            "details": d.get("details"), "created_at": d["created_at"],
        }
        for d in docs
    ]
