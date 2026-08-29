from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from app.models.review import ReviewTargetType, ReviewStatus, ReviewReplyReportReason


class CreateReviewRequest(BaseModel):
    booking_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)
    photos: List[str] = []


class UpdateReviewRequest(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)
    photos: Optional[List[str]] = None


class ReplyReviewRequest(BaseModel):
    reply_comment: str = Field(..., min_length=1, max_length=1000)


class ReportReviewRequest(BaseModel):
    reason: ReviewReplyReportReason
    comment: Optional[str] = None


class ModerateReviewRequest(BaseModel):
    status: ReviewStatus


class ReviewResponse(BaseModel):
    id: str
    target_type: ReviewTargetType
    target_id: str
    author_id: str
    author_name: Optional[str] = None
    author_avatar_url: Optional[str] = None
    booking_id: str
    rating: int
    comment: Optional[str] = None
    photos: List[str] = []
    reply_comment: Optional[str] = None
    reply_at: Optional[datetime] = None
    status: ReviewStatus
    report_count: int = 0
    helpful_count: int = 0
    created_at: datetime
    updated_at: datetime


class ReviewListResponse(BaseModel):
    items: List[ReviewResponse]
    total: int
    page: int
    page_size: int
    average_rating: float
    rating_breakdown: Dict[str, int]
