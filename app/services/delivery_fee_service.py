"""Frais de livraison des produits artisanaux (§19).

Les commandes en mode « livraison » sont confiées à une agence de livraison.
Les frais sont calculés automatiquement à partir d'une grille par région de
destination, gérée par l'admin. Une règle de région `"*"` sert de tarif par
défaut quand la région du client n'a pas d'entrée dédiée.
"""
from datetime import datetime
from typing import Optional

from bson import ObjectId
from pymongo import ReturnDocument
from fastapi import HTTPException, status

from app.core.database import get_database
from app.services import delivery_agency_service
from app.schemas.artisan import (
    UpsertDeliveryFeeRuleRequest,
    DeliveryFeeRuleResponse,
    DeliveryFeeQuote,
)

RULES_COLLECTION = "artisan_delivery_fee_rules"
DEFAULT_REGION_KEY = "*"


def _normalize_region(region: str) -> str:
    return region.strip().lower()


def _rule_to_response(doc: dict) -> DeliveryFeeRuleResponse:
    return DeliveryFeeRuleResponse(
        id=str(doc["_id"]),
        region=doc["region"],
        fee=doc["fee"],
        currency=doc.get("currency", "XOF"),
        agency_id=doc.get("agency_id"),
        delivery_provider=doc.get("delivery_provider"),
        free_delivery_threshold=doc.get("free_delivery_threshold"),
        eta_days_min=doc.get("eta_days_min"),
        eta_days_max=doc.get("eta_days_max"),
        active=doc.get("active", True),
        updated_at=doc["updated_at"],
    )


async def upsert_rule(data: UpsertDeliveryFeeRuleRequest) -> DeliveryFeeRuleResponse:
    db = get_database()
    now = datetime.utcnow()
    region = data.region.strip()
    region_key = DEFAULT_REGION_KEY if region == DEFAULT_REGION_KEY else _normalize_region(region)
    doc = data.model_dump()
    doc["region"] = region
    doc["region_key"] = region_key
    doc["updated_at"] = now
    # Dénormalise le nom de l'agence (valide au passage l'agency_id fourni).
    if data.agency_id:
        agency = await delivery_agency_service.get_agency(data.agency_id)  # 404 si inconnu
        doc["delivery_provider"] = agency.name
    else:
        doc["delivery_provider"] = None
    result = await db[RULES_COLLECTION].find_one_and_update(
        {"region_key": region_key},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return _rule_to_response(result)


async def list_rules(include_inactive: bool = True) -> list:
    db = get_database()
    query: dict = {} if include_inactive else {"active": True}
    docs = await db[RULES_COLLECTION].find(query).sort("region", 1).to_list(length=None)
    return [_rule_to_response(d) for d in docs]


async def delete_rule(rule_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(rule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle de frais de livraison introuvable")
    result = await db[RULES_COLLECTION].delete_one({"_id": ObjectId(rule_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle de frais de livraison introuvable")


async def _resolve_rule(region: str) -> Optional[dict]:
    """Règle applicable : région exacte (active) sinon règle par défaut ("*")."""
    db = get_database()
    region_key = _normalize_region(region)
    rule = await db[RULES_COLLECTION].find_one({"region_key": region_key, "active": True})
    if rule:
        return rule
    return await db[RULES_COLLECTION].find_one({"region_key": DEFAULT_REGION_KEY, "active": True})


async def compute_delivery_fee(region: Optional[str], subtotal: float) -> DeliveryFeeQuote:
    """Calcule les frais de livraison pour une région de destination et un sous-total.

    - Aucune règle configurée -> 400 (l'admin doit renseigner au moins un tarif par défaut).
    - Sous-total >= seuil de gratuité -> frais à 0.
    """
    if not region or not region.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La région de destination est obligatoire pour une livraison",
        )

    rule = await _resolve_rule(region)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune grille de frais de livraison n'est configurée. Contactez l'administrateur.",
        )

    fee = float(rule["fee"])
    threshold = rule.get("free_delivery_threshold")
    free_applied = threshold is not None and subtotal >= float(threshold)
    if free_applied:
        fee = 0.0

    return DeliveryFeeQuote(
        region=region.strip(),
        matched_region=rule["region"],
        subtotal=round(subtotal, 2),
        delivery_fee=round(fee, 2),
        free_delivery_applied=free_applied,
        total=round(subtotal + fee, 2),
        currency=rule.get("currency", "XOF"),
        agency_id=rule.get("agency_id"),
        delivery_provider=rule.get("delivery_provider"),
        eta_days_min=rule.get("eta_days_min"),
        eta_days_max=rule.get("eta_days_max"),
    )
