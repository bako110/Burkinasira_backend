from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    USER_SUSPENDED = "user_suspended"
    USER_REACTIVATED = "user_reactivated"
    ROLE_CHANGED = "role_changed"
    CONTENT_MODERATED = "content_moderated"
    PROVIDER_VALIDATED = "provider_validated"
    PROVIDER_SUSPENDED = "provider_suspended"
    COMMISSION_UPDATED = "commission_updated"
    SETTINGS_CHANGED = "settings_changed"


class AuditLogEntry(BaseModel):
    """Journal d'audit des actions administratives sensibles (§43)."""
    id: Optional[str] = Field(default=None, alias="_id")
    actor_id: str
    action: AuditAction
    target_type: Optional[str] = None  # ex: "user", "hotel", "review"
    target_id: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class PlatformCommissionSetting(BaseModel):
    """Commission appliquée par la plateforme, par type d'offre."""
    id: Optional[str] = Field(default=None, alias="_id")
    item_type: str
    commission_percent: float
    updated_by: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
