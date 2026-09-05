from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ConversationKind(str, Enum):
    TOURISTE_GUIDE = "touriste_guide"
    TOURISTE_HOTEL = "touriste_hotel"
    TOURISTE_RESTAURANT = "touriste_restaurant"
    TOURISTE_ARTISAN = "touriste_artisan"
    TOURISTE_TRANSPORT = "touriste_transport"
    # Tourisme communautaire : touriste <-> hôte d'une expérience
    # (rencontre habitant, hébergement chez l'habitant, visite de village...).
    TOURISTE_HOTE = "touriste_hote"
    ENTREPRISE_PRESTATAIRE = "entreprise_prestataire"
    SUPPORT_CLIENT = "support_client"
    GROUPE_VOYAGEURS = "groupe_voyageurs"


class MessageAttachmentType(str, Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    LOCATION = "location"


class MessageAttachment(BaseModel):
    type: MessageAttachmentType
    url: Optional[str] = None  # pour image/document
    latitude: Optional[float] = None  # pour location
    longitude: Optional[float] = None


class ChatMessage(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    conversation_id: str
    sender_id: str
    content: Optional[str] = None
    attachments: List[MessageAttachment] = []
    read_by: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class Conversation(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    kind: ConversationKind
    participant_ids: List[str]
    linked_booking_id: Optional[str] = None
    group_id: Optional[str] = None
    last_message_preview: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
