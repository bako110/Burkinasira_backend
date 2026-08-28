from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.passport import ChallengeStatus
from app.schemas.passport import (
    CreateBadgeRequest,
    BadgeResponse,
    CreateChallengeRequest,
    ChallengeResponse,
    CollectStampRequest,
    PassportResponse,
    LeaderboardEntry,
)

BADGES_COLLECTION = "passport_badges"
CHALLENGES_COLLECTION = "passport_challenges"
PASSPORTS_COLLECTION = "travel_passports"

POINTS_PER_STAMP = 10


# --- Badges ---

def _badge_to_response(doc: dict) -> BadgeResponse:
    return BadgeResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        description=doc["description"],
        category=doc["category"],
        icon_url=doc.get("icon_url"),
        criteria=doc.get("criteria"),
    )


async def create_badge(data: CreateBadgeRequest) -> BadgeResponse:
    db = get_database()
    doc = data.model_dump()
    doc["created_at"] = datetime.utcnow()
    result = await db[BADGES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _badge_to_response(doc)


async def list_badges() -> list:
    db = get_database()
    docs = await db[BADGES_COLLECTION].find({}).to_list(length=None)
    return [_badge_to_response(d) for d in docs]


# --- Défis ---

def _challenge_to_response(doc: dict) -> ChallengeResponse:
    return ChallengeResponse(
        id=str(doc["_id"]),
        title=doc["title"],
        description=doc["description"],
        target_count=doc.get("target_count", 1),
        related_category=doc.get("related_category"),
        reward_badge_id=doc.get("reward_badge_id"),
        status=doc.get("status", ChallengeStatus.ACTIVE.value),
    )


async def create_challenge(data: CreateChallengeRequest) -> ChallengeResponse:
    db = get_database()
    doc = data.model_dump()
    doc["status"] = ChallengeStatus.ACTIVE.value
    doc["created_at"] = datetime.utcnow()
    result = await db[CHALLENGES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _challenge_to_response(doc)


async def list_active_challenges() -> list:
    db = get_database()
    docs = await db[CHALLENGES_COLLECTION].find({"status": ChallengeStatus.ACTIVE.value}).to_list(length=None)
    return [_challenge_to_response(d) for d in docs]


# --- Passeport ---

def _passport_to_response(doc: dict) -> PassportResponse:
    return PassportResponse(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        stamps=doc.get("stamps", []),
        earned_badge_ids=doc.get("earned_badge_ids", []),
        challenge_progress=doc.get("challenge_progress", []),
        points=doc.get("points", 0),
        updated_at=doc["updated_at"],
    )


async def get_or_create_passport(user_id: str) -> dict:
    db = get_database()
    doc = await db[PASSPORTS_COLLECTION].find_one({"user_id": user_id})
    if not doc:
        now = datetime.utcnow()
        new_doc = {
            "user_id": user_id, "stamps": [], "earned_badge_ids": [],
            "challenge_progress": [], "points": 0, "created_at": now, "updated_at": now,
        }
        result = await db[PASSPORTS_COLLECTION].insert_one(new_doc)
        new_doc["_id"] = result.inserted_id
        doc = new_doc
    return doc


async def get_my_passport(user_id: str) -> PassportResponse:
    doc = await get_or_create_passport(user_id)
    return _passport_to_response(doc)


async def collect_stamp(data: CollectStampRequest, user_id: str) -> PassportResponse:
    from app.services import destination_service
    destination = await destination_service.get_destination(data.destination_id)  # 404 si inexistant

    db = get_database()
    doc = await get_or_create_passport(user_id)

    already_collected = any(s["destination_id"] == data.destination_id for s in doc.get("stamps", []))
    if already_collected:
        return _passport_to_response(doc)

    new_stamp = {
        "destination_id": data.destination_id,
        "destination_name": destination.name,
        "collected_at": datetime.utcnow(),
    }

    await db[PASSPORTS_COLLECTION].update_one(
        {"_id": doc["_id"]},
        {
            "$push": {"stamps": new_stamp},
            "$inc": {"points": POINTS_PER_STAMP},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )

    await _update_challenge_progress(doc["_id"], user_id)

    updated = await db[PASSPORTS_COLLECTION].find_one({"_id": doc["_id"]})
    return _passport_to_response(updated)


async def _update_challenge_progress(passport_id, user_id: str) -> None:
    db = get_database()
    passport = await db[PASSPORTS_COLLECTION].find_one({"_id": passport_id})
    stamp_count = len(passport.get("stamps", []))

    challenges = await db[CHALLENGES_COLLECTION].find({"status": ChallengeStatus.ACTIVE.value}).to_list(length=None)
    progress_list = passport.get("challenge_progress", [])
    progress_by_id = {p["challenge_id"]: p for p in progress_list}

    for challenge in challenges:
        cid = str(challenge["_id"])
        entry = progress_by_id.get(cid, {"challenge_id": cid, "current_count": 0, "completed": False, "completed_at": None})
        entry["current_count"] = stamp_count
        if not entry["completed"] and stamp_count >= challenge.get("target_count", 1):
            entry["completed"] = True
            entry["completed_at"] = datetime.utcnow()
            if challenge.get("reward_badge_id"):
                await db[PASSPORTS_COLLECTION].update_one(
                    {"_id": passport_id},
                    {"$addToSet": {"earned_badge_ids": challenge["reward_badge_id"]}},
                )
        progress_by_id[cid] = entry

    await db[PASSPORTS_COLLECTION].update_one(
        {"_id": passport_id},
        {"$set": {"challenge_progress": list(progress_by_id.values())}},
    )


async def get_leaderboard(limit: int = 20) -> list:
    from app.services import user_service
    db = get_database()
    docs = await db[PASSPORTS_COLLECTION].find({}).sort("points", -1).limit(limit).to_list(length=limit)

    entries = []
    for d in docs:
        try:
            user = await user_service.get_user_by_id(d["user_id"])
            display_name = user.full_name
        except Exception:
            display_name = "Utilisateur"
        entries.append(LeaderboardEntry(
            user_id=d["user_id"],
            display_name=display_name,
            points=d.get("points", 0),
            stamp_count=len(d.get("stamps", [])),
        ))
    return entries
