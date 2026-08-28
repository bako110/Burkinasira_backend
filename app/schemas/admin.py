from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.admin import AuditAction
from app.models.user import UserRole, UserStatus


class NationalDashboardResponse(BaseModel):
    total_users: int
    total_providers: int
    total_bookings: int
    pending_operator_applications: int
    pending_verifications: int
    open_disputes: int
    open_incident_reports: int


class AuditLogResponse(BaseModel):
    id: str
    actor_id: str
    action: AuditAction
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime


class ChangeUserStatusRequest(BaseModel):
    status: UserStatus
    reason: Optional[str] = None


class ChangeUserRoleRequest(BaseModel):
    role: UserRole


class AdminUserSummary(BaseModel):
    id: str
    full_name: str
    email: str
    role: UserRole
    status: UserStatus
    is_verified: bool
    created_at: datetime


class SetCommissionRequest(BaseModel):
    item_type: str
    commission_percent: float = Field(..., ge=0, le=100)


class CommissionResponse(BaseModel):
    item_type: str
    commission_percent: float
    updated_at: datetime
