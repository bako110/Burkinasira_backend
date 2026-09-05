from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint


class PostType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    CARNET_VOYAGE = "carnet_voyage"
    RECOMMANDATION = "recommandation"


class PostStatus(str, Enum):
    PUBLISHED = "published"
    FLAGGED = "flagged"
    REMOVED = "removed"


class CommunityPost(BaseModel):
    """Publication communauté (§27)."""
    id: Optional[str] = Field(default=None, alias="_id")
    author_id: str
    type: PostType
    caption: Optional[str] = None
    media_urls: List[str] = []
    related_destination_id: Optional[str] = None
    # Expérience communautaire vécue et racontée dans ce post / carnet de voyage.
    related_experience_id: Optional[str] = None
    group_id: Optional[str] = None
    location: Optional[GeoPoint] = None
    like_count: int = 0
    comment_count: int = 0
    status: PostStatus = PostStatus.PUBLISHED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class Comment(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    post_id: str
    author_id: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class FavoriteList(BaseModel):
    """Liste de favoris / lieux à visiter."""
    id: Optional[str] = Field(default=None, alias="_id")
    owner_id: str
    name: str
    destination_ids: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class TravelerGroup(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None
    cover_photo: Optional[str] = None
    region: Optional[str] = None  # ex: "Hauts-Bassins" ou pays pour un groupe international
    province: Optional[str] = None
    theme: Optional[str] = None  # ex: "randonnée", "gastronomie", "diaspora"
    creator_id: str
    member_ids: List[str] = []
    conversation_id: Optional[str] = None
    is_public: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class QuestionStatus(str, Enum):
    OPEN = "open"
    ANSWERED = "answered"


class CommunityQuestion(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    author_id: str
    title: str
    content: str
    related_destination_id: Optional[str] = None
    status: QuestionStatus = QuestionStatus.OPEN
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class QuestionAnswer(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    question_id: str
    author_id: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class ReportedContentType(str, Enum):
    POST = "post"
    COMMENT = "comment"
    QUESTION = "question"
    ANSWER = "answer"


class ContentReportStatus(str, Enum):
    REPORTED = "reported"
    REVIEWING = "reviewing"
    ACTION_TAKEN = "action_taken"
    DISMISSED = "dismissed"


class ContentReport(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    reporter_id: str
    content_type: ReportedContentType
    content_id: str
    reason: str
    status: ContentReportStatus = ContentReportStatus.REPORTED
    moderated_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
