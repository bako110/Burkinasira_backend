from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database

# Association item_type -> (collection, champ propriétaire)
_PROVIDER_LOOKUP = {
    "hotel": ("hotels", "owner_id"),
    "restaurant": ("restaurants", "owner_id"),
    "transport": ("transport_providers", "owner_id"),
    "guide": ("guide_profiles", "user_id"),
    "event": ("events", "organizer_id"),
    "experience": ("experiences", "host_id"),
}


async def resolve_owner_id(item_type: str, item_id: str) -> str | None:
    """Point d'entrée unique pour retrouver le propriétaire d'un item, quel que soit son type
    (y compris "product", cas particulier résolu via son profil artisan)."""
    if item_type == "product":
        return await resolve_product_owner_id(item_id)
    return await resolve_provider_id(item_type, item_id)


async def resolve_product_owner_id(product_id: str) -> str | None:
    """Cas particulier "product" : le propriétaire n'est pas sur le produit lui-même
    mais sur son profil artisan (product.artisan_id -> artisans.user_id)."""
    if not ObjectId.is_valid(product_id):
        return None
    db = get_database()
    product = await db["artisan_products"].find_one({"_id": ObjectId(product_id)}, {"artisan_id": 1})
    if not product or not ObjectId.is_valid(product.get("artisan_id", "")):
        return None
    artisan = await db["artisans"].find_one({"_id": ObjectId(product["artisan_id"])}, {"user_id": 1})
    return artisan.get("user_id") if artisan else None


async def resolve_provider_id(item_type: str, item_id: str) -> str | None:
    """Retrouve le user_id du prestataire propriétaire d'un item réservable.

    Retourne None si item_type n'a pas de notion de propriétaire (ex:
    "activity", "visit") ou si l'item est introuvable.
    """
    lookup = _PROVIDER_LOOKUP.get(item_type)
    if not lookup or not ObjectId.is_valid(item_id):
        return None
    collection, owner_field = lookup
    db = get_database()
    doc = await db[collection].find_one({"_id": ObjectId(item_id)}, {owner_field: 1})
    if not doc:
        return None
    return doc.get(owner_field)


async def is_authorized_for_establishment(item_type: str, item_id: str, user_id: str) -> bool:
    """Vrai si user_id est le propriétaire de l'établissement, ou un membre d'équipe
    actif spécifiquement rattaché à ce même établissement (ex: gérant d'une succursale)."""
    owner_id = await resolve_owner_id(item_type, item_id)
    if owner_id == user_id:
        return True

    db = get_database()
    member = await db["pro_team_members"].find_one({
        "user_id": user_id,
        "establishment_type": item_type,
        "establishment_id": item_id,
        "is_active": True,
    })
    return member is not None


async def resolve_real_price(item_type: str, item_id: str, room_type_name: Optional[str] = None) -> Optional[tuple]:
    """Retrouve le prix RÉEL (unit_price, currency) d'un item réservable en base,
    pour empêcher un client de fournir un prix arbitraire à la création d'une
    réservation. Retourne None si ce type d'item n'a pas de prix source fiable
    (ex: restaurant sans plat précisé, transport sans devis) — dans ce cas
    l'appelant doit décider d'une politique de repli explicite.
    """
    if not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    db = get_database()

    if item_type == "hotel":
        hotel = await db["hotels"].find_one({"_id": ObjectId(item_id)}, {"room_types": 1})
        if not hotel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hébergement introuvable")
        room_types = hotel.get("room_types", [])
        if not room_types:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet hébergement n'a aucun type de chambre configuré")
        if room_type_name:
            room = next((r for r in room_types if r["name"] == room_type_name), None)
            if not room:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type de chambre introuvable")
        else:
            room = room_types[0]
        return (room["price_per_night"], room.get("currency", "XOF"))

    if item_type == "event":
        event = await db["events"].find_one({"_id": ObjectId(item_id)}, {"ticket_price": 1, "currency": 1})
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
        return (event.get("ticket_price") or 0.0, event.get("currency", "XOF"))

    if item_type == "guide":
        guide = await db["guide_profiles"].find_one({"_id": ObjectId(item_id)}, {"daily_rate": 1, "currency": 1})
        if not guide:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guide introuvable")
        if guide.get("daily_rate") is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce guide n'a pas de tarif journalier configuré")
        return (guide["daily_rate"], guide.get("currency", "XOF"))

    return None


async def resolve_guide_hourly_rate(guide_id: str) -> Optional[tuple]:
    """Tarif horaire réel d'un guide, utilisé pour calculer le prix d'une
    réservation basée sur un créneau (slot_id) plutôt qu'une journée entière."""
    if not ObjectId.is_valid(guide_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guide introuvable")
    db = get_database()
    guide = await db["guide_profiles"].find_one({"_id": ObjectId(guide_id)}, {"hourly_rate": 1, "currency": 1})
    if not guide:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guide introuvable")
    if guide.get("hourly_rate") is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce guide n'a pas de tarif horaire configuré")
    return (guide["hourly_rate"], guide.get("currency", "XOF"))


async def list_managed_establishment_ids(user_id: str, item_type: str) -> list:
    """IDs des établissements d'un type donné auxquels user_id a accès en tant que membre
    d'équipe actif (mais dont il n'est pas le propriétaire) — ex: le gérant d'une succursale."""
    db = get_database()
    docs = await db["pro_team_members"].find(
        {"user_id": user_id, "establishment_type": item_type, "is_active": True},
        {"establishment_id": 1},
    ).to_list(length=None)
    return [d["establishment_id"] for d in docs if d.get("establishment_id")]
