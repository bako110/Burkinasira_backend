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
