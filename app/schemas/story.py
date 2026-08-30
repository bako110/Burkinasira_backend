from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.story import CultureContentType, CultureMediaType


class CreateCultureContentRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    type: CultureContentType
    media_type: CultureMediaType = CultureMediaType.TEXTE
    summary: Optional[str] = None
    content: Optional[str] = None
    media_url: Optional[str] = None
    cover_photo: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    related_destination_ids: List[str] = []
    author: Optional[str] = None


class UpdateCultureContentRequest(BaseModel):
    title: Optional[str] = None
    type: Optional[CultureContentType] = None
    media_type: Optional[CultureMediaType] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    media_url: Optional[str] = None
    cover_photo: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    related_destination_ids: Optional[List[str]] = None
    author: Optional[str] = None


class CultureContentSummary(BaseModel):
    id: str
    title: str
    type: CultureContentType
    media_type: CultureMediaType
    summary: Optional[str] = None
    cover_photo: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None


class CultureContentDetail(BaseModel):
    id: str
    title: str
    type: CultureContentType
    media_type: CultureMediaType
    summary: Optional[str] = None
    content: Optional[str] = None
    media_url: Optional[str] = None
    cover_photo: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    related_destination_ids: List[str]
    author: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CultureContentListResponse(BaseModel):
    items: List[CultureContentSummary]
    total: int
    page: int
    page_size: int


class CreateCulturalRouteRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    step_destination_ids: List[str] = []
    step_content_ids: List[str] = []


class UpdateCulturalRouteRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    step_destination_ids: Optional[List[str]] = None
    step_content_ids: Optional[List[str]] = None


class CulturalRouteResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    step_destination_ids: List[str]
    step_content_ids: List[str]
    created_at: datetime
