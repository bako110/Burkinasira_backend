from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.schemas.notification import (
    CreateNotificationRequest,
    NotificationResponse,
    UpdatePreferencesRequest,
    NotificationPreferencesResponse,
)
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list)
async def list_my_notifications(
    unread_only: bool = False,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Centre de notifications push + in-app (§41)."""
    return await notification_service.list_my_notifications(current_user.sub, unread_only)


@router.post("", response_model=Optional[NotificationResponse], status_code=status.HTTP_201_CREATED)
async def create_notification(
    data: CreateNotificationRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin/Système) Émettre une notification vers un utilisateur (null si la catégorie est désactivée par l'utilisateur)."""
    return await notification_service.create_notification(data)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(notification_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Marquer une notification comme lue."""
    return await notification_service.mark_as_read(notification_id, current_user.sub)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_as_read(current_user: TokenPayload = Depends(get_current_user)):
    """Marquer toutes les notifications comme lues."""
    await notification_service.mark_all_as_read(current_user.sub)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Supprimer une notification."""
    await notification_service.delete_notification(notification_id, current_user.sub)


@router.get("/preferences/me", response_model=NotificationPreferencesResponse)
async def get_my_preferences(current_user: TokenPayload = Depends(get_current_user)):
    """Ses préférences de notification par catégorie."""
    return await notification_service.get_or_create_preferences(current_user.sub)


@router.patch("/preferences/me", response_model=NotificationPreferencesResponse)
async def update_my_preferences(
    data: UpdatePreferencesRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Gérer ses préférences de notification par catégorie."""
    return await notification_service.update_preferences(current_user.sub, data)
