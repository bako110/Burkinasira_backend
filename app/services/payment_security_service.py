from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.payment_security import TransactionStatus
from app.schemas.payment_security import (
    ConfirmTransactionRequest,
    TransactionResponse,
    FlagSuspiciousActivityRequest,
    SuspiciousFlagResponse,
)

TRANSACTIONS_COLLECTION = "payment_transactions"
FLAGS_COLLECTION = "suspicious_payment_flags"

_index_ensured = False


async def _ensure_indexes(db) -> None:
    global _index_ensured
    if _index_ensured:
        return
    await db[TRANSACTIONS_COLLECTION].create_index("idempotency_key", unique=True)
    _index_ensured = True


def _to_response(doc: dict) -> TransactionResponse:
    return TransactionResponse(
        id=str(doc["_id"]),
        booking_id=doc["booking_id"],
        payer_id=doc["payer_id"],
        amount=doc["amount"],
        currency=doc.get("currency", "XOF"),
        status=doc.get("status", TransactionStatus.PENDING.value),
        payment_method=doc.get("payment_method"),
        created_at=doc["created_at"],
    )


async def confirm_transaction(data: ConfirmTransactionRequest, payer_id: str) -> TransactionResponse:
    """Confirme une transaction — protégée contre le double paiement via idempotency_key unique."""
    db = get_database()
    await _ensure_indexes(db)

    existing = await db[TRANSACTIONS_COLLECTION].find_one({"idempotency_key": data.idempotency_key})
    if existing:
        return _to_response(existing)

    now = datetime.utcnow()
    doc = data.model_dump()
    doc["payer_id"] = payer_id
    doc["status"] = TransactionStatus.CONFIRMED.value
    doc["created_at"] = now
    doc["updated_at"] = now

    try:
        result = await db[TRANSACTIONS_COLLECTION].insert_one(doc)
    except Exception:
        existing = await db[TRANSACTIONS_COLLECTION].find_one({"idempotency_key": data.idempotency_key})
        if existing:
            return _to_response(existing)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transaction déjà en cours de traitement")

    doc["_id"] = result.inserted_id
    return _to_response(doc)


async def list_my_transactions(payer_id: str) -> list:
    db = get_database()
    docs = await db[TRANSACTIONS_COLLECTION].find({"payer_id": payer_id}).sort("created_at", -1).to_list(length=None)
    return [_to_response(d) for d in docs]


async def get_transaction(transaction_id: str, current_user_id: str, is_admin: bool) -> TransactionResponse:
    db = get_database()
    if not ObjectId.is_valid(transaction_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction introuvable")
    doc = await db[TRANSACTIONS_COLLECTION].find_one({"_id": ObjectId(transaction_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction introuvable")
    if doc["payer_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    return _to_response(doc)


async def mark_refunded(transaction_id: str) -> TransactionResponse:
    db = get_database()
    if not ObjectId.is_valid(transaction_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction introuvable")
    result = await db[TRANSACTIONS_COLLECTION].update_one(
        {"_id": ObjectId(transaction_id)},
        {"$set": {"status": TransactionStatus.REFUNDED.value, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction introuvable")
    doc = await db[TRANSACTIONS_COLLECTION].find_one({"_id": ObjectId(transaction_id)})
    return _to_response(doc)


# --- Activité suspecte ---

def _flag_to_response(doc: dict) -> SuspiciousFlagResponse:
    return SuspiciousFlagResponse(
        id=str(doc["_id"]),
        transaction_id=doc.get("transaction_id"),
        reporter_id=doc["reporter_id"],
        type=doc["type"],
        details=doc.get("details"),
        created_at=doc["created_at"],
    )


async def flag_suspicious_activity(data: FlagSuspiciousActivityRequest, reporter_id: str) -> SuspiciousFlagResponse:
    db = get_database()
    doc = data.model_dump()
    doc["reporter_id"] = reporter_id
    doc["created_at"] = datetime.utcnow()
    result = await db[FLAGS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _flag_to_response(doc)


async def list_flags() -> list:
    db = get_database()
    docs = await db[FLAGS_COLLECTION].find({}).sort("created_at", -1).to_list(length=None)
    return [_flag_to_response(d) for d in docs]
