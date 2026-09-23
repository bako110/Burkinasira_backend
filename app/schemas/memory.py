from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.memory import MemoryTargetType, MemoryMediaType, MemoryStatus


class CreateMemoryRequest(BaseModel):
    target_type: MemoryTargetType
    target_id: str
    media_url: str
    media_type: MemoryMediaType
    title: Optional[str] = Field(default=None, max_length=120)
    caption: Optional[str] = Field(default=None, max_length=500)


class MemoryResponse(BaseModel):
    id: str
    target_type: MemoryTargetType
    target_id: str
    author_id: str
    author_name: Optional[str] = None
    author_avatar_url: Optional[str] = None
    media_url: str
    media_type: MemoryMediaType
    title: Optional[str] = None
    caption: Optional[str] = None
    status: MemoryStatus
    created_at: datetime


class MemoryListResponse(BaseModel):
    items: List[MemoryResponse]
    total: int
    page: int
    page_size: int


class ModerateMemoryRequest(BaseModel):
    status: MemoryStatus
