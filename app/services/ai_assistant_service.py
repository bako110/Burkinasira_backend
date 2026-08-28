from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.core.config import settings
from app.models.ai_assistant import AIConversationType, MessageRole
from app.schemas.ai_assistant import (
    SendMessageRequest,
    ConversationResponse,
    ConversationSummary,
    MessageResponse,
    TranslationRequest,
    TranslationResponse,
    CulturalSummaryRequest,
    CulturalSummaryResponse,
    GenerateItineraryRequest,
    GenerateItineraryResponse,
)

COLLECTION = "ai_conversations"


async def _call_ai_provider(system_prompt: str, user_message: str) -> str:
    """
    Point d'intégration avec le fournisseur LLM (ex: Claude API).
    Aucune clé API n'est configurée dans l'environnement actuel
    (voir app/core/config.py — pas de champ ANTHROPIC_API_KEY/OPENAI_API_KEY).
    À implémenter lors du Lot 4 avec la clé fournie.
    """
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="GoTours AI n'est pas encore configuré (clé API du fournisseur LLM manquante).",
    )


def _conversation_to_response(doc: dict) -> ConversationResponse:
    return ConversationResponse(
        id=str(doc["_id"]),
        type=doc.get("type", AIConversationType.GENERAL.value),
        title=doc.get("title"),
        messages=[
            MessageResponse(role=m["role"], content=m["content"], created_at=m["created_at"])
            for m in doc.get("messages", [])
        ],
        updated_at=doc["updated_at"],
    )


def _conversation_to_summary(doc: dict) -> ConversationSummary:
    return ConversationSummary(
        id=str(doc["_id"]),
        type=doc.get("type", AIConversationType.GENERAL.value),
        title=doc.get("title"),
        updated_at=doc["updated_at"],
    )


async def send_message(data: SendMessageRequest, user_id: str) -> ConversationResponse:
    db = get_database()
    now = datetime.utcnow()

    if data.conversation_id:
        if not ObjectId.is_valid(data.conversation_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
        doc = await db[COLLECTION].find_one({"_id": ObjectId(data.conversation_id), "user_id": user_id})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    else:
        doc = {
            "user_id": user_id,
            "type": data.type.value,
            "title": data.message[:60],
            "messages": [],
            "context": data.context,
            "created_at": now,
            "updated_at": now,
        }
        result = await db[COLLECTION].insert_one(doc)
        doc["_id"] = result.inserted_id

    user_msg = {"role": MessageRole.USER.value, "content": data.message, "created_at": now}

    ai_reply_text = await _call_ai_provider(
        system_prompt=f"GoTours AI — assistant touristique Burkina Faso, type: {data.type.value}",
        user_message=data.message,
    )
    assistant_msg = {"role": MessageRole.ASSISTANT.value, "content": ai_reply_text, "created_at": datetime.utcnow()}

    await db[COLLECTION].update_one(
        {"_id": doc["_id"]},
        {
            "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )
    doc = await db[COLLECTION].find_one({"_id": doc["_id"]})
    return _conversation_to_response(doc)


async def list_my_conversations(user_id: str) -> list:
    db = get_database()
    docs = await db[COLLECTION].find({"user_id": user_id}).sort("updated_at", -1).to_list(length=None)
    return [_conversation_to_summary(d) for d in docs]


async def get_conversation(conversation_id: str, user_id: str) -> ConversationResponse:
    db = get_database()
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(conversation_id), "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    return _conversation_to_response(doc)


async def translate_text(data: TranslationRequest) -> TranslationResponse:
    translated = await _call_ai_provider(
        system_prompt=f"Traduis ce texte en {data.target_language}, réponds uniquement avec la traduction.",
        user_message=data.text,
    )
    return TranslationResponse(original_text=data.text, translated_text=translated, target_language=data.target_language)


async def get_cultural_summary(data: CulturalSummaryRequest) -> CulturalSummaryResponse:
    from app.services import destination_service
    destination = await destination_service.get_destination(data.destination_id)

    summary = await _call_ai_provider(
        system_prompt="Résume en 3-4 phrases l'intérêt culturel et historique de ce lieu.",
        user_message=f"{destination.name}: {destination.description}\n{destination.history or ''}",
    )
    return CulturalSummaryResponse(destination_id=data.destination_id, summary=summary)


async def generate_itinerary(data: GenerateItineraryRequest, user_id: str) -> GenerateItineraryResponse:
    proposal = await _call_ai_provider(
        system_prompt="Propose un itinéraire de voyage touristique au Burkina Faso.",
        user_message=(
            f"Région: {data.region or 'toutes'}, durée: {data.duration_days} jours, "
            f"budget: {data.budget_estimate} {data.currency}, thèmes: {', '.join(data.themes)}. "
            f"Notes: {data.notes or ''}"
        ),
    )
    return GenerateItineraryResponse(trip_id=None, proposal=proposal)
