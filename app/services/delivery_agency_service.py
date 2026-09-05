"""Agences de livraison des produits artisanaux (§19).

Gérées par l'admin. Chaque agence déclare les régions qu'elle dessert ; la
grille des frais de livraison (`delivery_fee_service`) référence une agence par
son identifiant.
"""
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.schemas.artisan import (
    CreateDeliveryAgencyRequest,
    UpdateDeliveryAgencyRequest,
    DeliveryAgencyResponse,
)

COLLECTION = "delivery_agencies"


def _to_response(doc: dict) -> DeliveryAgencyResponse:
    return DeliveryAgencyResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        contact_phone=doc.get("contact_phone"),
        contact_email=doc.get("contact_email"),
        covered_regions=doc.get("covered_regions", []),
        manager_user_id=doc.get("manager_user_id"),
        active=doc.get("active", True),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_agency(data: CreateDeliveryAgencyRequest) -> DeliveryAgencyResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["covered_regions"] = [r.strip() for r in doc.get("covered_regions", []) if r and r.strip()]
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_response(doc)


async def list_agencies(include_inactive: bool = True) -> list:
    db = get_database()
    query: dict = {} if include_inactive else {"active": True}
    docs = await db[COLLECTION].find(query).sort("name", 1).to_list(length=None)
    return [_to_response(d) for d in docs]


async def get_agency(agency_id: str) -> DeliveryAgencyResponse:
    doc = await _get_agency_doc(agency_id)
    return _to_response(doc)


async def _get_agency_doc(agency_id: str) -> dict:
    db = get_database()
    if not ObjectId.is_valid(agency_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agence de livraison introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(agency_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agence de livraison introuvable")
    return doc


async def update_agency(agency_id: str, data: UpdateDeliveryAgencyRequest) -> DeliveryAgencyResponse:
    db = get_database()
    doc = await _get_agency_doc(agency_id)
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if "covered_regions" in update_fields:
        update_fields["covered_regions"] = [
            r.strip() for r in update_fields["covered_regions"] if r and r.strip()
        ]
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[COLLECTION].update_one({"_id": doc["_id"]}, {"$set": update_fields})
    return await get_agency(agency_id)


async def delete_agency(agency_id: str) -> None:
    db = get_database()
    doc = await _get_agency_doc(agency_id)
    # Refuse la suppression si une règle de frais y fait encore référence.
    rule = await db["artisan_delivery_fee_rules"].find_one({"agency_id": str(doc["_id"])})
    if rule:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette agence est encore utilisée par une règle de frais de livraison",
        )
    await db[COLLECTION].delete_one({"_id": doc["_id"]})


async def get_agency_name(agency_id: Optional[str]) -> Optional[str]:
    if not agency_id:
        return None
    db = get_database()
    if not ObjectId.is_valid(agency_id):
        return None
    doc = await db[COLLECTION].find_one({"_id": ObjectId(agency_id)}, {"name": 1})
    return doc["name"] if doc else None


async def resolve_agency_for_region(region: str) -> Optional[dict]:
    """Agence active desservant la région (couverture explicite, ou couvre tout)."""
    db = get_database()
    region_norm = region.strip().lower()
    async for doc in db[COLLECTION].find({"active": True}):
        covered = [r.strip().lower() for r in doc.get("covered_regions", [])]
        if not covered or region_norm in covered:
            return doc
    return None
