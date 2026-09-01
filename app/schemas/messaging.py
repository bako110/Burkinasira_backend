from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.messaging import ConversationKind, MessageAttachment


class StartConversationRequest(BaseModel):
    kind: ConversationKind
    other_user_id: str
    linked_booking_id: Optional[str] = None
    initial_message: str = Field(..., min_length=1)


class SendChatMessageRequest(BaseModel):
    content: Optional[str] = None
    attachments: List[MessageAttachment] = []


class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    content: Optional[str] = None
    attachments: List[MessageAttachment]
    read_by: List[str]
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    kind: ConversationKind
    participant_ids: List[str]
    linked_booking_id: Optional[str] = None
    group_id: Optional[str] = None
    last_message_preview: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    display_name: Optional[str] = None
    display_avatar_url: Optional[str] = None


class ContactSupportRequest(BaseModel):
    subject: str = Field(..., min_length=2, max_length=200)
    message: str = Field(..., min_length=5)
