"""Backfill du champ `slug` pour les documents existants (créés avant l'introduction des slugs).

Usage: python -m scripts.backfill_slugs
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import connect_to_mongo, get_database, close_mongo_connection
from app.utils.slug import generate_unique_slug, ensure_slug_index

# (collection, champ source du nom)
TARGETS = [
    ("hotels", "name"),
    ("restaurants", "name"),
    ("transport_providers", "name"),
    ("guide_profiles", "display_name"),
    ("events", "title"),
    ("health_facilities", "name"),
    ("money_service_points", "name"),
    ("connectivity_points", "name"),
    ("culture_contents", "title"),
    ("artisan_products", "name"),
]


async def backfill_collection(db, collection: str, name_field: str, force: bool = False) -> int:
    await ensure_slug_index(db, collection)
    if force:
        await db[collection].update_many({}, {"$unset": {"slug": ""}})
    cursor = db[collection].find({"slug": {"$exists": False}})
    count = 0
    async for doc in cursor:
        source_text = doc.get(name_field) or str(doc["_id"])
        slug = await generate_unique_slug(db, collection, source_text)
        await db[collection].update_one({"_id": doc["_id"]}, {"$set": {"slug": slug}})
        count += 1
    return count


async def main():
    force = "--force" in sys.argv
    await connect_to_mongo()
    db = get_database()
    total = 0
    for collection, name_field in TARGETS:
        n = await backfill_collection(db, collection, name_field, force=force)
        print(f"{collection}: {n} document(s) mis à jour")
        total += n
    print(f"Total: {total} document(s) mis à jour")
    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
