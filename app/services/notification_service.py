from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.core.realtime import manager
from app.models.notification import NotificationCategory
from app.schemas.notification import (
    CreateNotificationRequest,
    NotificationResponse,
    UpdatePreferencesRequest,
    NotificationPreferencesResponse,
)

NOTIFICATIONS_COLLECTION = "notifications"
PREFERENCES_COLLECTION = "notification_preferences"

ALL_CATEGORIES = [c.value for c in NotificationCategory]


def _to_response(doc: dict) -> NotificationResponse:
    return NotificationResponse(
        id=str(doc["_id"]),
        category=doc["category"],
        title=doc["title"],
        body=doc["body"],
        related_id=doc.get("related_id"),
        is_read=doc.get("is_read", False),
        created_at=doc["created_at"],
    )


async def _is_category_enabled(user_id: str, category: str) -> bool:
    db = get_database()
    prefs = await db[PREFERENCES_COLLECTION].find_one({"user_id": user_id})
    if not prefs:
        return True
    return category in prefs.get("enabled_categories", ALL_CATEGORIES)


async def create_notification(data: CreateNotificationRequest) -> Optional[NotificationResponse]:
    """Créer une notification, en respectant les préférences de l'utilisateur."""
    if not await _is_category_enabled(data.user_id, data.category.value):
        return None

    db = get_database()
    doc = data.model_dump()
    doc["is_read"] = False
    doc["created_at"] = datetime.utcnow()
    result = await db[NOTIFICATIONS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    response = _to_response(doc)

    await manager.send_to_user(data.user_id, "notification.new", response.model_dump())
    return response


async def list_my_notifications(user_id: str, unread_only: bool = False) -> list:
    db = get_database()
    query: dict = {"user_id": user_id}
    if unread_only:
        query["is_read"] = False
    docs = await db[NOTIFICATIONS_COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_to_response(d) for d in docs]


async def mark_as_read(notification_id: str, user_id: str) -> NotificationResponse:
    db = get_database()
    if not ObjectId.is_valid(notification_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification introuvable")
    doc = await db[NOTIFICATIONS_COLLECTION].find_one({"_id": ObjectId(notification_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification introuvable")
    if doc["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")

    await db[NOTIFICATIONS_COLLECTION].update_one({"_id": ObjectId(notification_id)}, {"$set": {"is_read": True}})
    doc["is_read"] = True
    return _to_response(doc)


async def mark_all_as_read(user_id: str) -> None:
    db = get_database()
    await db[NOTIFICATIONS_COLLECTION].update_many({"user_id": user_id, "is_read": False}, {"$set": {"is_read": True}})


async def delete_notification(notification_id: str, user_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(notification_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification introuvable")
    doc = await db[NOTIFICATIONS_COLLECTION].find_one({"_id": ObjectId(notification_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification introuvable")
    if doc["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    await db[NOTIFICATIONS_COLLECTION].delete_one({"_id": ObjectId(notification_id)})


# --- Préférences ---

async def get_or_create_preferences(user_id: str) -> NotificationPreferencesResponse:
    db = get_database()
    doc = await db[PREFERENCES_COLLECTION].find_one({"user_id": user_id})
    if not doc:
        doc = {
            "user_id": user_id, "enabled_categories": ALL_CATEGORIES,
            "push_enabled": True, "in_app_enabled": True, "updated_at": datetime.utcnow(),
        }
        await db[PREFERENCES_COLLECTION].insert_one(doc)
    return NotificationPreferencesResponse(
        user_id=doc["user_id"],
        enabled_categories=doc.get("enabled_categories", ALL_CATEGORIES),
        push_enabled=doc.get("push_enabled", True),
        in_app_enabled=doc.get("in_app_enabled", True),
    )


async def update_preferences(user_id: str, data: UpdatePreferencesRequest) -> NotificationPreferencesResponse:
    db = get_database()
    update_fields = {}
    if data.enabled_categories is not None:
        update_fields["enabled_categories"] = [c.value if isinstance(c, NotificationCategory) else c for c in data.enabled_categories]
    if data.push_enabled is not None:
        update_fields["push_enabled"] = data.push_enabled
    if data.in_app_enabled is not None:
        update_fields["in_app_enabled"] = data.in_app_enabled

    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[PREFERENCES_COLLECTION].update_one({"user_id": user_id}, {"$set": update_fields}, upsert=True)

    return await get_or_create_preferences(user_id)
