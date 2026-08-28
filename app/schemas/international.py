from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.international import FirstVisitGuideCategory


class CreateGuideEntryRequest(BaseModel):
    category: FirstVisitGuideCategory
    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=5)
    language: str = "fr"


class UpdateGuideEntryRequest(BaseModel):
    category: Optional[FirstVisitGuideCategory] = None
    title: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None


class GuideEntryResponse(BaseModel):
    id: str
    category: FirstVisitGuideCategory
    title: str
    content: str
    language: str
    updated_at: datetime


class SupportedLanguageResponse(BaseModel):
    code: str
    label: str
    is_active: bool
