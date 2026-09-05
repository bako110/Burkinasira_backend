"""Règlement des frais de livraison aux agences (§19).

Chaque commande livrée en mode « livraison » avec des frais > 0 génère un
montant dû à l'agence (`settlement_status = "pending"`). L'admin consulte le dû
par agence puis marque un lot de commandes comme réglé, ce qui crée une trace
de règlement (`delivery_settlements`).
"""
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.models.artisan import ArtisanOrderStatus, DeliverySettlementStatus
from app.services import delivery_agency_service
from app.schemas.artisan import (
    DeliveryDueLine,
    DeliveryDueResponse,
    CreateSettlementRequest,
    SettlementResponse,
)

ORDERS_COLLECTION = "artisan_orders"
SETTLEMENTS_COLLECTION = "delivery_settlements"


async def list_due_by_agency() -> DeliveryDueResponse:
    """Montants dus aux agences : commandes livrées, frais > 0, non réglées."""
    db = get_database()
    query = {
        "status": ArtisanOrderStatus.DELIVERED.value,
        "settlement_status": DeliverySettlementStatus.PENDING.value,
        "delivery_fee": {"$gt": 0},
    }
    groups: dict = {}
    async for order in db[ORDERS_COLLECTION].find(query):
        key = (order.get("agency_id"), order.get("currency", "XOF"))
        g = groups.setdefault(key, {"count": 0, "total": 0.0, "ids": []})
        g["count"] += 1
        g["total"] += float(order.get("delivery_fee", 0.0))
        g["ids"].append(str(order["_id"]))

    lines = []
    grand_total = 0.0
    for (agency_id, currency), g in groups.items():
        grand_total += g["total"]
        lines.append(
            DeliveryDueLine(
                agency_id=agency_id,
                agency_name=await delivery_agency_service.get_agency_name(agency_id),
                currency=currency,
                order_count=g["count"],
                total_due=round(g["total"], 2),
                order_ids=g["ids"],
            )
        )
    lines.sort(key=lambda l: l.total_due, reverse=True)
    return DeliveryDueResponse(lines=lines, grand_total=round(grand_total, 2))


def _settlement_to_response(doc: dict, agency_name: Optional[str] = None) -> SettlementResponse:
    return SettlementResponse(
        id=str(doc["_id"]),
        agency_id=doc["agency_id"],
        agency_name=agency_name if agency_name is not None else doc.get("agency_name"),
        currency=doc.get("currency", "XOF"),
        order_ids=doc.get("order_ids", []),
        order_count=len(doc.get("order_ids", [])),
        total_amount=doc.get("total_amount", 0.0),
        reference=doc.get("reference"),
        note=doc.get("note"),
        settled_by=doc.get("settled_by"),
        created_at=doc["created_at"],
    )


async def settle(data: CreateSettlementRequest, actor_id: str) -> SettlementResponse:
    db = get_database()
    agency = await delivery_agency_service.get_agency(data.agency_id)  # 404 si inconnu

    obj_ids = []
    for oid in data.order_ids:
        if not ObjectId.is_valid(oid):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Identifiant de commande invalide : {oid}")
        obj_ids.append(ObjectId(oid))

    orders = await db[ORDERS_COLLECTION].find({"_id": {"$in": obj_ids}}).to_list(length=None)
    found_ids = {str(o["_id"]) for o in orders}
    missing = [oid for oid in data.order_ids if oid not in found_ids]
    if missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Commandes introuvables : {', '.join(missing)}")

    total = 0.0
    currency = None
    for o in orders:
        if o.get("agency_id") != data.agency_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La commande {o['_id']} n'est pas rattachée à cette agence",
            )
        if o.get("status") != ArtisanOrderStatus.DELIVERED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La commande {o['_id']} n'est pas encore livrée",
            )
        if o.get("settlement_status") != DeliverySettlementStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La commande {o['_id']} n'est pas en attente de règlement",
            )
        if currency is None:
            currency = o.get("currency", "XOF")
        elif o.get("currency", "XOF") != currency:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Toutes les commandes d'un règlement doivent avoir la même devise",
            )
        total += float(o.get("delivery_fee", 0.0))

    now = datetime.utcnow()
    settlement_doc = {
        "agency_id": data.agency_id,
        "agency_name": agency.name,
        "currency": currency or "XOF",
        "order_ids": data.order_ids,
        "total_amount": round(total, 2),
        "reference": data.reference,
        "note": data.note,
        "settled_by": actor_id,
        "created_at": now,
    }
    result = await db[SETTLEMENTS_COLLECTION].insert_one(settlement_doc)
    settlement_doc["_id"] = result.inserted_id

    await db[ORDERS_COLLECTION].update_many(
        {"_id": {"$in": obj_ids}},
        {"$set": {
            "settlement_status": DeliverySettlementStatus.SETTLED.value,
            "settled_at": now,
            "settlement_id": str(result.inserted_id),
            "updated_at": now,
        }},
    )
    return _settlement_to_response(settlement_doc, agency_name=agency.name)


async def list_settlements(agency_id: Optional[str] = None) -> list:
    db = get_database()
    query: dict = {}
    if agency_id:
        query["agency_id"] = agency_id
    docs = await db[SETTLEMENTS_COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_settlement_to_response(d) for d in docs]
