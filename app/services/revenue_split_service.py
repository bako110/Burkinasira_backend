from datetime import datetime
from typing import Optional
from bson import ObjectId
from pymongo import ReturnDocument
from fastapi import HTTPException, status
from app.core.database import get_database
from app.schemas.revenue_split import (
    CreateRevenueSplitRuleRequest,
    RevenueSplitRuleResponse,
    RevenueSplitBreakdown,
)

RULES_COLLECTION = "revenue_split_rules"


def _rule_to_response(doc: dict) -> RevenueSplitRuleResponse:
    return RevenueSplitRuleResponse(
        id=str(doc["_id"]),
        item_type=doc["item_type"],
        provider_percent=doc["provider_percent"],
        guide_percent=doc.get("guide_percent", 0.0),
        community_percent=doc.get("community_percent", 0.0),
        transport_percent=doc.get("transport_percent", 0.0),
        taxes_percent=doc.get("taxes_percent", 0.0),
        platform_commission_percent=doc["platform_commission_percent"],
        notes=doc.get("notes"),
        updated_at=doc["updated_at"],
    )


async def set_rule(data: CreateRevenueSplitRuleRequest) -> RevenueSplitRuleResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["updated_at"] = now
    result = await db[RULES_COLLECTION].find_one_and_update(
        {"item_type": data.item_type},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return _rule_to_response(result)


async def list_rules() -> list:
    db = get_database()
    docs = await db[RULES_COLLECTION].find({}).to_list(length=None)
    return [_rule_to_response(d) for d in docs]


async def get_rule(item_type: str) -> Optional[dict]:
    db = get_database()
    return await db[RULES_COLLECTION].find_one({"item_type": item_type})


async def get_breakdown_for_booking(booking_id: str) -> RevenueSplitBreakdown:
    db = get_database()
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    booking = await db["bookings"].find_one({"_id": ObjectId(booking_id)})
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")

    rule = await get_rule(booking["item_type"])
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Répartition non disponible pour ce type de réservation",
        )

    total = booking["total_price"]
    return RevenueSplitBreakdown(
        item_type=booking["item_type"],
        total_amount=total,
        currency=booking.get("currency", "XOF"),
        provider_amount=round(total * rule["provider_percent"] / 100, 2),
        guide_amount=round(total * rule.get("guide_percent", 0.0) / 100, 2),
        community_amount=round(total * rule.get("community_percent", 0.0) / 100, 2),
        transport_amount=round(total * rule.get("transport_percent", 0.0) / 100, 2),
        taxes_amount=round(total * rule.get("taxes_percent", 0.0) / 100, 2),
        platform_commission_amount=round(total * rule["platform_commission_percent"] / 100, 2),
    )
