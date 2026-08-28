from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.notification import NotificationCategory


class CreateNotificationRequest(BaseModel):
    user_id: str
    category: NotificationCategory
    title: str = Field(..., min_length=1, max_length=150)
    body: str = Field(..., min_length=1)
    related_id: Optional[str] = None


class NotificationResponse(BaseModel):
    id: str
    category: NotificationCategory
    title: str
    body: str
    related_id: Optional[str] = None
    is_read: bool
    created_at: datetime


class UpdatePreferencesRequest(BaseModel):
    enabled_categories: Optional[List[NotificationCategory]] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None


class NotificationPreferencesResponse(BaseModel):
    user_id: str
    enabled_categories: List[NotificationCategory]
    push_enabled: bool
    in_app_enabled: bool
