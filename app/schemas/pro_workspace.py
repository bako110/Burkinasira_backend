from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.pro_workspace import PromotionStatus, TeamMemberRole


class ProDashboardResponse(BaseModel):
    provider_id: str
    total_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    total_revenue: float
    currency: str
    average_rating: float
    review_count: int


class CreatePromotionRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    discount_percent: Optional[float] = Field(default=None, ge=0, le=100)
    applies_to_item_type: str
    applies_to_item_id: str
    valid_from: datetime
    valid_until: datetime


class PromotionResponse(BaseModel):
    id: str
    provider_id: str
    title: str
    description: Optional[str] = None
    discount_percent: Optional[float] = None
    applies_to_item_type: str
    applies_to_item_id: str
    valid_from: datetime
    valid_until: datetime
    status: PromotionStatus


class InviteTeamMemberRequest(BaseModel):
    email: str
    full_name: str = Field(..., min_length=2, max_length=150)
    temporary_password: str = Field(..., min_length=6)
    role: TeamMemberRole = TeamMemberRole.STAFF
    establishment_type: Optional[str] = None
    establishment_id: Optional[str] = None


class TeamMemberResponse(BaseModel):
    id: str
    provider_id: str
    user_id: Optional[str] = None
    email: str
    role: TeamMemberRole
    establishment_type: Optional[str] = None
    establishment_id: Optional[str] = None
    is_active: bool
    account_created: bool = False
