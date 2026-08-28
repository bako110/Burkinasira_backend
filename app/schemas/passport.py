from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.passport import BadgeCategory, ChallengeStatus, Stamp, UserChallengeProgress


class CreateBadgeRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str
    category: BadgeCategory
    icon_url: Optional[str] = None
    criteria: Optional[str] = None


class BadgeResponse(BaseModel):
    id: str
    name: str
    description: str
    category: BadgeCategory
    icon_url: Optional[str] = None
    criteria: Optional[str] = None


class CreateChallengeRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: str
    target_count: int = Field(default=1, gt=0)
    related_category: Optional[str] = None
    reward_badge_id: Optional[str] = None


class ChallengeResponse(BaseModel):
    id: str
    title: str
    description: str
    target_count: int
    related_category: Optional[str] = None
    reward_badge_id: Optional[str] = None
    status: ChallengeStatus


class CollectStampRequest(BaseModel):
    destination_id: str


class PassportResponse(BaseModel):
    id: str
    user_id: str
    stamps: List[Stamp]
    earned_badge_ids: List[str]
    challenge_progress: List[UserChallengeProgress]
    points: int
    updated_at: datetime


class LeaderboardEntry(BaseModel):
    user_id: str
    display_name: str
    points: int
    stamp_count: int
