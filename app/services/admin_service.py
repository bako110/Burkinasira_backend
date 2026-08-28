from datetime import datetime
from typing import Optional
from bson import ObjectId
from pymongo import ReturnDocument
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.admin import AuditAction
from app.models.user import UserRole, UserStatus
from app.models.operator import OperatorApplicationStatus
from app.models.verified import VerificationStatus, DisputeStatus
from app.models.emergency import IncidentStatus
from app.schemas.admin import (
    NationalDashboardResponse,
    AuditLogResponse,
    ChangeUserStatusRequest,
    ChangeUserRoleRequest,
    AdminUserSummary,
    SetCommissionRequest,
    CommissionResponse,
)

AUDIT_COLLECTION = "audit_log"
COMMISSIONS_COLLECTION = "platform_commissions"


async def log_action(actor_id: str, action: AuditAction, target_type: Optional[str] = None, target_id: Optional[str] = None, details: Optional[str] = None) -> None:
    db = get_database()
    await db[AUDIT_COLLECTION].insert_one({
        "actor_id": actor_id,
        "action": action.value if isinstance(action, AuditAction) else action,
        "target_type": target_type,
        "target_id": target_id,
        "details": details,
        "created_at": datetime.utcnow(),
    })


async def list_audit_log(limit: int = 100) -> list:
    db = get_database()
    docs = await db[AUDIT_COLLECTION].find({}).sort("created_at", -1).limit(limit).to_list(length=limit)
    return [
        AuditLogResponse(
            id=str(d["_id"]), actor_id=d["actor_id"], action=d["action"],
            target_type=d.get("target_type"), target_id=d.get("target_id"),
            details=d.get("details"), created_at=d["created_at"],
        )
        for d in docs
    ]


async def get_national_dashboard() -> NationalDashboardResponse:
    db = get_database()
    return NationalDashboardResponse(
        total_users=await db["users"].count_documents({}),
        total_providers=await db["users"].count_documents({"role": UserRole.PROVIDER.value}),
        total_bookings=await db["bookings"].count_documents({"item_type": {"$exists": True}}),
        pending_operator_applications=await db["operator_applications"].count_documents({"status": OperatorApplicationStatus.SUBMITTED.value}),
        pending_verifications=await db["verification_requests"].count_documents({"status": VerificationStatus.PENDING.value}),
        open_disputes=await db["disputes"].count_documents({"status": DisputeStatus.OPEN.value}),
        open_incident_reports=await db["incident_reports"].count_documents({"status": IncidentStatus.REPORTED.value}),
    )


# --- Gestion des utilisateurs ---

async def list_users(role: Optional[UserRole] = None, status_filter: Optional[UserStatus] = None) -> list:
    db = get_database()
    query: dict = {}
    if role:
        query["role"] = role.value if isinstance(role, UserRole) else role
    if status_filter:
        query["status"] = status_filter.value if isinstance(status_filter, UserStatus) else status_filter
    docs = await db["users"].find(query).to_list(length=None)
    return [_doc_to_admin_summary(d) for d in docs]


def _doc_to_admin_summary(d: dict) -> AdminUserSummary:
    """Tolère les documents créés par l'ancien schéma (nom_complet, actif, verifiee, date_creation)."""
    return AdminUserSummary(
        id=str(d["_id"]),
        full_name=d.get("full_name") or d.get("nom_complet") or "Utilisateur",
        email=d["email"],
        role=d.get("role", UserRole.TOURIST.value),
        status=d.get("status") or (UserStatus.ACTIVE.value if d.get("actif", True) else UserStatus.SUSPENDED.value),
        is_verified=d.get("is_verified", d.get("verifiee", False)),
        created_at=d.get("created_at") or d.get("date_creation") or datetime.utcnow(),
    )


async def change_user_status(user_id: str, data: ChangeUserStatusRequest, actor_id: str) -> AdminUserSummary:
    db = get_database()
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    result = await db["users"].update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"status": data.status.value, "updated_at": datetime.utcnow()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    action = AuditAction.USER_SUSPENDED if data.status == UserStatus.SUSPENDED else AuditAction.USER_REACTIVATED
    await log_action(actor_id, action, target_type="user", target_id=user_id, details=data.reason)

    doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    return _doc_to_admin_summary(doc)


async def change_user_role(user_id: str, data: ChangeUserRoleRequest, actor_id: str) -> AdminUserSummary:
    db = get_database()
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    result = await db["users"].update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"role": data.role.value, "updated_at": datetime.utcnow()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    await log_action(actor_id, AuditAction.ROLE_CHANGED, target_type="user", target_id=user_id, details=f"Nouveau rôle: {data.role.value}")

    doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    return _doc_to_admin_summary(doc)


# --- Commissions ---

async def set_commission(data: SetCommissionRequest, actor_id: str) -> CommissionResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = await db[COMMISSIONS_COLLECTION].find_one_and_update(
        {"item_type": data.item_type},
        {"$set": {"commission_percent": data.commission_percent, "updated_by": actor_id, "updated_at": now}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    await log_action(actor_id, AuditAction.COMMISSION_UPDATED, target_type="commission", target_id=data.item_type)
    return CommissionResponse(item_type=doc["item_type"], commission_percent=doc["commission_percent"], updated_at=doc["updated_at"])


async def list_commissions() -> list:
    db = get_database()
    docs = await db[COMMISSIONS_COLLECTION].find({}).to_list(length=None)
    return [CommissionResponse(item_type=d["item_type"], commission_percent=d["commission_percent"], updated_at=d["updated_at"]) for d in docs]
