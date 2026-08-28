from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user
from app.schemas.auth import TokenPayload
from app.schemas.messaging import (
    StartConversationRequest,
    SendChatMessageRequest,
    ChatMessageResponse,
    ConversationResponse,
    ContactSupportRequest,
)
from app.services import messaging_service

router = APIRouter(prefix="/messaging", tags=["Messagerie et relation client"])


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    data: StartConversationRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Démarrer une conversation : touriste ↔ guide/hôtel/restaurant/artisan (§34)."""
    return await messaging_service.start_conversation(data, initiator_id=current_user.sub)


@router.get("/conversations", response_model=list)
async def list_my_conversations(current_user: TokenPayload = Depends(get_current_user)):
    """Ses fils de conversation."""
    return await messaging_service.list_my_conversations(current_user.sub)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Détail d'une conversation."""
    return await messaging_service.get_conversation(conversation_id, current_user.sub)


@router.get("/conversations/{conversation_id}/messages", response_model=list)
async def list_messages(conversation_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Messages d'une conversation."""
    return await messaging_service.list_messages(conversation_id, current_user.sub)


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: str,
    data: SendChatMessageRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Envoyer un message, une image, un document ou une localisation."""
    return await messaging_service.send_message(conversation_id, data, sender_id=current_user.sub)


@router.post("/conversations/{conversation_id}/link-booking/{booking_id}", response_model=ConversationResponse)
async def link_booking(
    conversation_id: str,
    booking_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Lier une réservation à la conversation."""
    return await messaging_service.link_booking(conversation_id, booking_id, current_user.sub)


@router.post("/support", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def contact_support(
    data: ContactSupportRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Contacter le service client."""
    return await messaging_service.contact_support(data, current_user.sub)
