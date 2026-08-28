from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class AIConversationType(str, Enum):
    GENERAL = "general"
    ITINERARY = "itinerary"
    TRANSLATION = "translation"
    CULTURAL_SUMMARY = "cultural_summary"
    PRO_WRITING_HELP = "pro_writing_help"
    BUSINESS_PLANNING = "business_planning"


class AIMessage(BaseModel):
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class AIConversation(BaseModel):
    """Fil de discussion avec l'assistant GoTours AI (§26)."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    type: AIConversationType = AIConversationType.GENERAL
    title: Optional[str] = None
    messages: List[AIMessage] = []
    context: dict = {}  # ex: {"trip_id": "...", "destination_id": "..."}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
