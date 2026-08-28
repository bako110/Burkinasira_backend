from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.schemas.ai_assistant import (
    SendMessageRequest,
    ConversationResponse,
    TranslationRequest,
    TranslationResponse,
    CulturalSummaryRequest,
    CulturalSummaryResponse,
    GenerateItineraryRequest,
    GenerateItineraryResponse,
)
from app.services import ai_assistant_service

router = APIRouter(prefix="/ai", tags=["IA — GoTours AI"])


@router.post("/messages", response_model=ConversationResponse)
async def send_message(
    data: SendMessageRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Dialoguer avec l'assistant conversationnel touristique (§26)."""
    return await ai_assistant_service.send_message(data, user_id=current_user.sub)


@router.get("/conversations", response_model=list)
async def list_my_conversations(current_user: TokenPayload = Depends(get_current_user)):
    """Historique de ses conversations avec GoTours AI."""
    return await ai_assistant_service.list_my_conversations(current_user.sub)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Détail d'une conversation."""
    return await ai_assistant_service.get_conversation(conversation_id, current_user.sub)


@router.post("/translate", response_model=TranslationResponse)
async def translate_text(
    data: TranslationRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Traduire ou obtenir une aide linguistique (§26, lié à §32 Tourisme international)."""
    return await ai_assistant_service.translate_text(data)


@router.post("/cultural-summary", response_model=CulturalSummaryResponse)
async def get_cultural_summary(
    data: CulturalSummaryRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Obtenir un résumé culturel d'un lieu."""
    return await ai_assistant_service.get_cultural_summary(data)


@router.post("/itinerary", response_model=GenerateItineraryResponse)
async def generate_itinerary(
    data: GenerateItineraryRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Créer un itinéraire assisté par IA, optimisé selon budget et temps (§26, lié à §25)."""
    return await ai_assistant_service.generate_itinerary(data, user_id=current_user.sub)
