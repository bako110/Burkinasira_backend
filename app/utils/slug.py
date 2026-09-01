import re
import unicodedata

from bson import ObjectId


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = ascii_text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


async def generate_unique_slug(db, collection: str, text: str) -> str:
    """Génère un slug unique pour `collection` à partir de `text`, en ajoutant
    un suffixe -2, -3, ... en cas de collision avec un document existant."""
    base = slugify(text) or "item"
    slug = base
    suffix = 2
    while await db[collection].find_one({"slug": slug}, {"_id": 1}):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


async def find_by_slug_or_id(db, collection: str, slug_or_id: str) -> dict | None:
    """Récupère un document par slug, ou par ObjectId si `slug_or_id` en est un valide."""
    if ObjectId.is_valid(slug_or_id):
        doc = await db[collection].find_one({"_id": ObjectId(slug_or_id)})
        if doc:
            return doc
    return await db[collection].find_one({"slug": slug_or_id})


_ensured_collections: set[str] = set()


async def ensure_slug_index(db, collection: str) -> None:
    if collection in _ensured_collections:
        return
    await db[collection].create_index("slug", unique=True, sparse=True)
    _ensured_collections.add(collection)
