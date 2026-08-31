from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint
from app.models.community import PostType, QuestionStatus, ReportedContentType


class CreatePostRequest(BaseModel):
    type: PostType
    caption: Optional[str] = None
    media_urls: List[str] = []
    related_destination_id: Optional[str] = None
    group_id: Optional[str] = None
    location: Optional[GeoPoint] = None


class PostResponse(BaseModel):
    id: str
    author_id: str
    author_name: Optional[str] = None
    author_avatar_url: Optional[str] = None
    type: PostType
    caption: Optional[str] = None
    media_urls: List[str]
    related_destination_id: Optional[str] = None
    group_id: Optional[str] = None
    location: Optional[GeoPoint] = None
    like_count: int
    comment_count: int
    is_liked_by_me: bool = False
    created_at: datetime


class PostListResponse(BaseModel):
    items: List[PostResponse]
    total: int
    page: int
    page_size: int


class CreateCommentRequest(BaseModel):
    content: str = Field(..., min_length=1)


class CommentResponse(BaseModel):
    id: str
    post_id: str
    author_id: str
    content: str
    created_at: datetime


class CreateFavoriteListRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class AddToFavoriteListRequest(BaseModel):
    destination_id: str


class FavoriteListResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    destination_ids: List[str]
    created_at: datetime


class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    cover_photo: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    theme: Optional[str] = None
    is_public: bool = True


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    cover_photo: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    theme: Optional[str] = None
    creator_id: str
    member_ids: List[str]
    conversation_id: Optional[str] = None
    is_public: bool
    created_at: datetime


class GroupMemberPublic(BaseModel):
    id: str
    full_name: str
    avatar_url: Optional[str] = None


class GroupDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    cover_photo: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    theme: Optional[str] = None
    creator_id: str
    members: List[GroupMemberPublic]
    conversation_id: Optional[str] = None
    is_public: bool
    created_at: datetime


class CreateQuestionRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=5)
    related_destination_id: Optional[str] = None


class QuestionResponse(BaseModel):
    id: str
    author_id: str
    title: str
    content: str
    related_destination_id: Optional[str] = None
    status: QuestionStatus
    created_at: datetime


class CreateAnswerRequest(BaseModel):
    content: str = Field(..., min_length=1)


class AnswerResponse(BaseModel):
    id: str
    question_id: str
    author_id: str
    content: str
    created_at: datetime


class ReportContentRequest(BaseModel):
    content_type: ReportedContentType
    content_id: str
    reason: str = Field(..., min_length=3)
