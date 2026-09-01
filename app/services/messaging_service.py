from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.core.realtime import manager
from app.models.messaging import ConversationKind
from app.models.notification import NotificationCategory
from app.schemas.messaging import (
    StartConversationRequest,
    SendChatMessageRequest,
    ChatMessageResponse,
    ConversationResponse,
    ContactSupportRequest,
)
from app.schemas.notification import CreateNotificationRequest
from app.services import notification_service

CONVERSATIONS_COLLECTION = "conversations"
MESSAGES_COLLECTION = "chat_messages"
USERS_COLLECTION = "users"
BOOKINGS_COLLECTION = "bookings"
GUIDE_PROFILES_COLLECTION = "guide_profiles"

SUPPORT_USER_ID = "fasoviva-support"

# Pour ces types de conversation, le nom affiché doit être celui de
# l'établissement réservé (hôtel, restaurant, artisan) plutôt que celui du
# propriétaire (other_user_id est son user_id, pas un nom d'établissement).
_ESTABLISHMENT_KINDS = {"touriste_hotel", "touriste_restaurant", "touriste_artisan"}


async def _resolve_display_name(doc: dict, current_user_id: str) -> tuple:
    """Nom (et avatar éventuel) à afficher pour cette conversation, du point de
    vue de current_user_id : le nom réel du correspondant (guide, touriste),
    ou le nom de l'établissement réservé (hôtel, restaurant, artisan)."""
    db = get_database()
    kind = doc["kind"]
    other_id = next((p for p in doc.get("participant_ids", []) if p != current_user_id), None)

    if other_id == SUPPORT_USER_ID:
        return ("BurkinaSira Support", None)

    if kind in _ESTABLISHMENT_KINDS and doc.get("linked_booking_id"):
        booking = await db[BOOKINGS_COLLECTION].find_one(
            {"_id": ObjectId(doc["linked_booking_id"])}, {"item_title": 1}
        ) if ObjectId.is_valid(doc["linked_booking_id"]) else None
        if booking and booking.get("item_title"):
            return (booking["item_title"], None)

    if not other_id or not ObjectId.is_valid(other_id):
        return (None, None)

    if kind == "touriste_guide":
        guide = await db[GUIDE_PROFILES_COLLECTION].find_one({"user_id": other_id}, {"display_name": 1, "photo_url": 1})
        if guide:
            return (guide.get("display_name"), guide.get("photo_url"))

    user = await db[USERS_COLLECTION].find_one({"_id": ObjectId(other_id)}, {"full_name": 1, "avatar_url": 1})
    if user:
        return (user.get("full_name"), user.get("avatar_url"))
    return (None, None)


async def _conversation_to_response(doc: dict, current_user_id: str) -> ConversationResponse:
    display_name, display_avatar_url = await _resolve_display_name(doc, current_user_id)
    return ConversationResponse(
        id=str(doc["_id"]),
        kind=doc["kind"],
        participant_ids=doc.get("participant_ids", []),
        linked_booking_id=doc.get("linked_booking_id"),
        group_id=doc.get("group_id"),
        last_message_preview=doc.get("last_message_preview"),
        last_message_at=doc.get("last_message_at"),
        created_at=doc["created_at"],
        display_name=display_name,
        display_avatar_url=display_avatar_url,
    )


def _message_to_response(doc: dict) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=str(doc["_id"]),
        conversation_id=doc["conversation_id"],
        sender_id=doc["sender_id"],
        content=doc.get("content"),
        attachments=doc.get("attachments", []),
        read_by=doc.get("read_by", []),
        created_at=doc["created_at"],
    )


def _check_participant(doc: dict, user_id: str) -> None:
    if user_id not in doc.get("participant_ids", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à cette conversation")


async def _create_message(conversation_id: str, sender_id: str, content: Optional[str], attachments: list) -> dict:
    db = get_database()
    now = datetime.utcnow()
    msg_doc = {
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "content": content,
        "attachments": [a if isinstance(a, dict) else a.model_dump() for a in attachments],
        "read_by": [sender_id],
        "created_at": now,
    }
    result = await db[MESSAGES_COLLECTION].insert_one(msg_doc)
    msg_doc["_id"] = result.inserted_id

    preview = content[:80] if content else "[pièce jointe]"
    conversation = await db[CONVERSATIONS_COLLECTION].find_one_and_update(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"last_message_preview": preview, "last_message_at": now}},
        return_document=True,
    )

    message_response = _message_to_response(msg_doc)
    recipients = [p for p in (conversation or {}).get("participant_ids", []) if p != sender_id and p != SUPPORT_USER_ID]
    for recipient_id in recipients:
        await manager.send_to_user(recipient_id, "message.new", message_response.model_dump())
        if not manager.is_online(recipient_id):
            await notification_service.create_notification(CreateNotificationRequest(
                user_id=recipient_id,
                category=NotificationCategory.MESSAGE_PRESTATAIRE,
                title="Nouveau message",
                body=preview,
                related_id=conversation_id,
            ))

    return msg_doc


async def start_conversation(data: StartConversationRequest, initiator_id: str) -> ConversationResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = {
        "kind": data.kind.value,
        "participant_ids": [initiator_id, data.other_user_id],
        "linked_booking_id": data.linked_booking_id,
        "last_message_preview": None,
        "last_message_at": None,
        "created_at": now,
    }
    result = await db[CONVERSATIONS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    await _create_message(str(doc["_id"]), initiator_id, data.initial_message, [])
    updated = await db[CONVERSATIONS_COLLECTION].find_one({"_id": doc["_id"]})
    return await _conversation_to_response(updated, initiator_id)


async def list_my_conversations(user_id: str) -> list:
    db = get_database()
    docs = await db[CONVERSATIONS_COLLECTION].find(
        {"participant_ids": user_id}
    ).sort("last_message_at", -1).to_list(length=None)
    return [await _conversation_to_response(d, user_id) for d in docs]


async def get_conversation(conversation_id: str, user_id: str) -> ConversationResponse:
    db = get_database()
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    doc = await db[CONVERSATIONS_COLLECTION].find_one({"_id": ObjectId(conversation_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    _check_participant(doc, user_id)
    return await _conversation_to_response(doc, user_id)


async def send_message(conversation_id: str, data: SendChatMessageRequest, sender_id: str) -> ChatMessageResponse:
    db = get_database()
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    doc = await db[CONVERSATIONS_COLLECTION].find_one({"_id": ObjectId(conversation_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    _check_participant(doc, sender_id)

    msg = await _create_message(conversation_id, sender_id, data.content, data.attachments)
    return _message_to_response(msg)


async def list_messages(conversation_id: str, user_id: str) -> list:
    db = get_database()
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    doc = await db[CONVERSATIONS_COLLECTION].find_one({"_id": ObjectId(conversation_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    _check_participant(doc, user_id)

    docs = await db[MESSAGES_COLLECTION].find({"conversation_id": conversation_id}).sort("created_at", 1).to_list(length=None)
    return [_message_to_response(d) for d in docs]


async def link_booking(conversation_id: str, booking_id: str, user_id: str) -> ConversationResponse:
    db = get_database()
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    doc = await db[CONVERSATIONS_COLLECTION].find_one({"_id": ObjectId(conversation_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    _check_participant(doc, user_id)

    await db[CONVERSATIONS_COLLECTION].update_one(
        {"_id": ObjectId(conversation_id)}, {"$set": {"linked_booking_id": booking_id}}
    )
    doc = await db[CONVERSATIONS_COLLECTION].find_one({"_id": ObjectId(conversation_id)})
    return await _conversation_to_response(doc, user_id)


async def create_group_conversation(group_id: str, creator_id: str) -> str:
    """Crée la conversation de groupe associée à un groupe de voyageurs (usage interne)."""
    db = get_database()
    now = datetime.utcnow()
    doc = {
        "kind": ConversationKind.GROUPE_VOYAGEURS.value,
        "participant_ids": [creator_id],
        "linked_booking_id": None,
        "group_id": group_id,
        "last_message_preview": None,
        "last_message_at": None,
        "created_at": now,
    }
    result = await db[CONVERSATIONS_COLLECTION].insert_one(doc)
    return str(result.inserted_id)


async def add_group_conversation_participant(conversation_id: str, user_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(conversation_id):
        return
    await db[CONVERSATIONS_COLLECTION].update_one(
        {"_id": ObjectId(conversation_id)},
        {"$addToSet": {"participant_ids": user_id}},
    )


async def remove_group_conversation_participant(conversation_id: str, user_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(conversation_id):
        return
    await db[CONVERSATIONS_COLLECTION].update_one(
        {"_id": ObjectId(conversation_id)},
        {"$pull": {"participant_ids": user_id}},
    )


async def contact_support(data: ContactSupportRequest, user_id: str) -> ConversationResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = {
        "kind": ConversationKind.SUPPORT_CLIENT.value,
        "participant_ids": [user_id, SUPPORT_USER_ID],
        "linked_booking_id": None,
        "last_message_preview": None,
        "last_message_at": None,
        "created_at": now,
    }
    result = await db[CONVERSATIONS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    await _create_message(str(doc["_id"]), user_id, f"[{data.subject}] {data.message}", [])
    updated = await db[CONVERSATIONS_COLLECTION].find_one({"_id": doc["_id"]})
    return await _conversation_to_response(updated, user_id)
