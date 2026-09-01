"""Backfill du champ share_token pour les voyages (trips) existants.

Usage: python -m scripts.backfill_trip_tokens
"""
import asyncio
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import connect_to_mongo, get_database, close_mongo_connection

COLLECTION = "trips"


async def main():
    await connect_to_mongo()
    db = get_database()
    await db[COLLECTION].create_index("share_token", unique=True, sparse=True)

    cursor = db[COLLECTION].find({"share_token": {"$exists": False}})
    count = 0
    async for doc in cursor:
        token = secrets.token_urlsafe(12)
        await db[COLLECTION].update_one({"_id": doc["_id"]}, {"$set": {"share_token": token}})
        count += 1
    print(f"{count} voyage(s) mis à jour")
    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
