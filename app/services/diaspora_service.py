from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.diaspora import DiasporaContentType, CommunityMeetupStatus
from app.schemas.diaspora import (
    CreateDiasporaContentRequest,
    UpdateDiasporaContentRequest,
    DiasporaContentResponse,
    CreateMeetupRequest,
    MeetupResponse,
)

CONTENT_COLLECTION = "diaspora_contents"
MEETUPS_COLLECTION = "diaspora_meetups"


# --- Contenu diaspora ---

def _content_to_response(doc: dict) -> DiasporaContentResponse:
    return DiasporaContentResponse(
        id=str(doc["_id"]),
        title=doc["title"],
        type=doc["type"],
        description=doc["description"],
        region=doc.get("region"),
        location=doc.get("location"),
        related_destination_id=doc.get("related_destination_id"),
        created_at=doc["created_at"],
    )


async def create_content(data: CreateDiasporaContentRequest, created_by: str) -> DiasporaContentResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["created_by"] = created_by
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[CONTENT_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _content_to_response(doc)


async def list_content(
    type: Optional[DiasporaContentType] = None,
    region: Optional[str] = None,
    q: Optional[str] = None,
) -> list:
    db = get_database()
    query: dict = {}
    if type:
        query["type"] = type.value if isinstance(type, DiasporaContentType) else type
    if region:
        query["region"] = region
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    docs = await db[CONTENT_COLLECTION].find(query).to_list(length=None)
    return [_content_to_response(d) for d in docs]


async def get_content(content_id: str) -> DiasporaContentResponse:
    db = get_database()
    if not ObjectId.is_valid(content_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu introuvable")
    doc = await db[CONTENT_COLLECTION].find_one({"_id": ObjectId(content_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu introuvable")
    return _content_to_response(doc)


async def update_content(content_id: str, data: UpdateDiasporaContentRequest) -> DiasporaContentResponse:
    db = get_database()
    if not ObjectId.is_valid(content_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[CONTENT_COLLECTION].update_one({"_id": ObjectId(content_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu introuvable")
    return await get_content(content_id)


async def delete_content(content_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(content_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu introuvable")
    result = await db[CONTENT_COLLECTION].delete_one({"_id": ObjectId(content_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenu introuvable")


# --- Rencontres communautaires ---

def _meetup_to_response(doc: dict) -> MeetupResponse:
    return MeetupResponse(
        id=str(doc["_id"]),
        organizer_id=doc["organizer_id"],
        title=doc["title"],
        description=doc.get("description"),
        region=doc["region"],
        location=doc.get("location"),
        scheduled_at=doc["scheduled_at"],
        status=doc.get("status", CommunityMeetupStatus.PLANNED.value),
        participant_ids=doc.get("participant_ids", []),
    )


async def create_meetup(data: CreateMeetupRequest, organizer_id: str) -> MeetupResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["organizer_id"] = organizer_id
    doc["status"] = CommunityMeetupStatus.PLANNED.value
    doc["participant_ids"] = []
    doc["created_at"] = now
    result = await db[MEETUPS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _meetup_to_response(doc)


async def list_meetups(region: Optional[str] = None) -> list:
    db = get_database()
    query: dict = {"status": CommunityMeetupStatus.PLANNED.value}
    if region:
        query["region"] = region
    docs = await db[MEETUPS_COLLECTION].find(query).sort("scheduled_at", 1).to_list(length=None)
    return [_meetup_to_response(d) for d in docs]


async def join_meetup(meetup_id: str, user_id: str) -> MeetupResponse:
    db = get_database()
    if not ObjectId.is_valid(meetup_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rencontre introuvable")
    result = await db[MEETUPS_COLLECTION].update_one(
        {"_id": ObjectId(meetup_id)}, {"$addToSet": {"participant_ids": user_id}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rencontre introuvable")
    doc = await db[MEETUPS_COLLECTION].find_one({"_id": ObjectId(meetup_id)})
    return _meetup_to_response(doc)
