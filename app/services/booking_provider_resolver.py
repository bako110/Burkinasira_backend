from bson import ObjectId
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
