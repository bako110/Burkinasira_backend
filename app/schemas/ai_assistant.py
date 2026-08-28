from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.ai_assistant import AIConversationType, MessageRole


class SendMessageRequest(BaseModel):
    conversation_id: Optional[str] = None
    type: AIConversationType = AIConversationType.GENERAL
    message: str = Field(..., min_length=1)
    context: dict = {}


class MessageResponse(BaseModel):
    role: MessageRole
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    type: AIConversationType
    title: Optional[str] = None
    messages: List[MessageResponse]
    updated_at: datetime


class ConversationSummary(BaseModel):
    id: str
    type: AIConversationType
    title: Optional[str] = None
    updated_at: datetime


class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_language: str


class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    target_language: str


class CulturalSummaryRequest(BaseModel):
    destination_id: str


class CulturalSummaryResponse(BaseModel):
    destination_id: str
    summary: str


class GenerateItineraryRequest(BaseModel):
    region: Optional[str] = None
    duration_days: int = Field(..., gt=0, le=60)
    budget_estimate: Optional[float] = None
    currency: str = "XOF"
    themes: List[str] = []
    notes: Optional[str] = None


class GenerateItineraryResponse(BaseModel):
    trip_id: Optional[str] = None
    proposal: str
