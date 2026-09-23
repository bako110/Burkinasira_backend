from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from livekit import api as lk_api

from app.core.config import settings
from app.core.database import get_database
from app.models.community import LiveSessionStatus
from app.schemas.community import StartLiveRequest, LiveSessionResponse, LiveTokenResponse

LIVE_SESSIONS_COLLECTION = "live_sessions"
USERS_COLLECTION = "users"


def _require_livekit_enabled() -> None:
    if not settings.livekit_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le live n'est pas encore configuré sur ce serveur (LIVEKIT_URL/API_KEY/API_SECRET manquants).",
        )


def _room_name_for(session_id: ObjectId) -> str:
    return f"live-{session_id}"


async def _session_to_response(doc: dict) -> LiveSessionResponse:
    db = get_database()
    host_doc = await db[USERS_COLLECTION].find_one({"_id": ObjectId(doc["host_id"])}) if ObjectId.is_valid(doc["host_id"]) else None
    return LiveSessionResponse(
        id=str(doc["_id"]),
        host_id=doc["host_id"],
        host_name=host_doc.get("full_name") if host_doc else None,
        host_avatar_url=host_doc.get("avatar_url") if host_doc else None,
        title=doc["title"],
        description=doc.get("description"),
        group_id=doc.get("group_id"),
        room_name=doc["room_name"],
        status=doc.get("status", LiveSessionStatus.LIVE),
        viewer_count=doc.get("viewer_count", 0),
        started_at=doc["started_at"],
        ended_at=doc.get("ended_at"),
    )


async def start_live(data: StartLiveRequest, host_id: str) -> LiveSessionResponse:
    """Démarre une session de live : crée le document, puis la room LiveKit correspondante."""
    _require_livekit_enabled()
    db = get_database()

    # Un hôte ne peut diffuser qu'un seul live à la fois.
    existing = await db[LIVE_SESSIONS_COLLECTION].find_one(
        {"host_id": host_id, "status": LiveSessionStatus.LIVE.value}
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous avez déjà un live en cours. Terminez-le avant d'en démarrer un nouveau.",
        )

    if data.group_id and not ObjectId.is_valid(data.group_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="group_id invalide")

    now = datetime.utcnow()
    doc = {
        "host_id": host_id,
        "title": data.title,
        "description": data.description,
        "group_id": data.group_id,
        "status": LiveSessionStatus.LIVE.value,
        "viewer_count": 0,
        "started_at": now,
        "ended_at": None,
    }
    result = await db[LIVE_SESSIONS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    room_name = _room_name_for(doc["_id"])
    doc["room_name"] = room_name
    await db[LIVE_SESSIONS_COLLECTION].update_one({"_id": doc["_id"]}, {"$set": {"room_name": room_name}})

    async with lk_api.LiveKitAPI(settings.LIVEKIT_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) as lk:
        await lk.room.create_room(lk_api.CreateRoomRequest(name=room_name, empty_timeout=300))

    return await _session_to_response(doc)


async def end_live(session_id: str, user_id: str) -> LiveSessionResponse:
    _require_livekit_enabled()
    db = get_database()
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live introuvable")
    doc = await db[LIVE_SESSIONS_COLLECTION].find_one({"_id": ObjectId(session_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live introuvable")
    if doc["host_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul l'hôte peut terminer ce live")

    now = datetime.utcnow()
    await db[LIVE_SESSIONS_COLLECTION].update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"status": LiveSessionStatus.ENDED.value, "ended_at": now}},
    )
    doc["status"] = LiveSessionStatus.ENDED.value
    doc["ended_at"] = now

    async with lk_api.LiveKitAPI(settings.LIVEKIT_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) as lk:
        try:
            await lk.room.delete_room(lk_api.DeleteRoomRequest(room=doc["room_name"]))
        except Exception:
            pass  # la room a peut-être déjà été fermée automatiquement (empty_timeout)

    return await _session_to_response(doc)


async def list_live_sessions(group_id: Optional[str] = None) -> list:
    db = get_database()
    query: dict = {"status": LiveSessionStatus.LIVE.value}
    if group_id:
        query["group_id"] = group_id
    docs = await db[LIVE_SESSIONS_COLLECTION].find(query).sort("started_at", -1).to_list(length=None)
    return [await _session_to_response(d) for d in docs]


async def get_live_session(session_id: str) -> LiveSessionResponse:
    db = get_database()
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live introuvable")
    doc = await db[LIVE_SESSIONS_COLLECTION].find_one({"_id": ObjectId(session_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live introuvable")
    return await _session_to_response(doc)


async def get_live_token(session_id: str, user_id: str, user_name: str) -> LiveTokenResponse:
    """Jeton d'accès LiveKit : l'hôte peut publier (caméra/micro), les autres
    membres ne font que regarder (et utiliser le chat texte de la room)."""
    _require_livekit_enabled()
    db = get_database()
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live introuvable")
    doc = await db[LIVE_SESSIONS_COLLECTION].find_one({"_id": ObjectId(session_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live introuvable")
    if doc.get("status") != LiveSessionStatus.LIVE.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce live est terminé")

    is_host = doc["host_id"] == user_id
    grants = lk_api.VideoGrants(
        room_join=True,
        room=doc["room_name"],
        can_publish=is_host,
        can_subscribe=True,
        can_publish_data=True,  # chat texte pendant le live, pour tout le monde
    )
    token = (
        lk_api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(user_id)
        .with_name(user_name)
        .with_grants(grants)
        .to_jwt()
    )

    return LiveTokenResponse(url=settings.LIVEKIT_URL, token=token, room_name=doc["room_name"], can_publish=is_host)
