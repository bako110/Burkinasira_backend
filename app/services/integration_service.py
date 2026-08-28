from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.integration import ConnectorType, ConnectorStatus
from app.schemas.integration import (
    UpdateConnectorRequest,
    ConnectorResponse,
    CreateWebhookRequest,
    WebhookResponse,
    ImportDataRequest,
)

CONNECTORS_COLLECTION = "integration_connectors"
WEBHOOKS_COLLECTION = "webhook_subscriptions"

IMPORTABLE_ITEM_TYPES = {"hotel", "restaurant"}


def _connector_to_response(doc: dict) -> ConnectorResponse:
    return ConnectorResponse(
        id=str(doc["_id"]),
        type=doc["type"],
        provider_name=doc["provider_name"],
        status=doc.get("status", ConnectorStatus.NOT_CONFIGURED.value),
        config_notes=doc.get("config_notes"),
        updated_at=doc["updated_at"],
    )


async def list_connectors() -> list:
    db = get_database()
    docs = await db[CONNECTORS_COLLECTION].find({}).to_list(length=None)
    return [_connector_to_response(d) for d in docs]


async def upsert_connector(connector_type: ConnectorType, data: UpdateConnectorRequest, actor_id: str) -> ConnectorResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["type"] = connector_type.value if isinstance(connector_type, ConnectorType) else connector_type
    doc["updated_by"] = actor_id
    doc["updated_at"] = now
    await db[CONNECTORS_COLLECTION].update_one(
        {"type": doc["type"]},
        {"$set": doc},
        upsert=True,
    )
    doc_after = await db[CONNECTORS_COLLECTION].find_one({"type": doc["type"]})
    return _connector_to_response(doc_after)


# --- Webhooks ---

def _webhook_to_response(doc: dict) -> WebhookResponse:
    return WebhookResponse(
        id=str(doc["_id"]),
        owner_id=doc["owner_id"],
        event_type=doc["event_type"],
        target_url=doc["target_url"],
        is_active=doc.get("is_active", True),
        created_at=doc["created_at"],
    )


async def create_webhook(data: CreateWebhookRequest, owner_id: str) -> WebhookResponse:
    db = get_database()
    doc = data.model_dump()
    doc["owner_id"] = owner_id
    doc["is_active"] = True
    doc["created_at"] = datetime.utcnow()
    result = await db[WEBHOOKS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _webhook_to_response(doc)


async def list_my_webhooks(owner_id: str) -> list:
    db = get_database()
    docs = await db[WEBHOOKS_COLLECTION].find({"owner_id": owner_id}).to_list(length=None)
    return [_webhook_to_response(d) for d in docs]


async def delete_webhook(webhook_id: str, owner_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(webhook_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook introuvable")
    doc = await db[WEBHOOKS_COLLECTION].find_one({"_id": ObjectId(webhook_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook introuvable")
    if doc["owner_id"] != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    await db[WEBHOOKS_COLLECTION].delete_one({"_id": ObjectId(webhook_id)})


async def trigger_webhooks(event_type: str, payload: dict) -> None:
    """Point d'appel interne — la livraison HTTP réelle sera ajoutée avec un provider de queue/HTTP."""
    db = get_database()
    subscriptions = await db[WEBHOOKS_COLLECTION].find({"event_type": event_type, "is_active": True}).to_list(length=None)
    # TODO: livraison HTTP réelle (hors périmètre sans infrastructure de queue configurée)
    return None


# --- Import de données (Pro) ---

async def import_data(data: ImportDataRequest, owner_id: str) -> dict:
    if data.item_type not in IMPORTABLE_ITEM_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type non importable. Types supportés: {', '.join(IMPORTABLE_ITEM_TYPES)}",
        )

    imported = 0
    errors = []

    if data.item_type == "hotel":
        from app.schemas.hotel import CreateHotelRequest
        from app.services import hotel_service
        for i, item in enumerate(data.items):
            try:
                req = CreateHotelRequest(**item)
                await hotel_service.create_hotel(req, owner_id=owner_id)
                imported += 1
            except Exception as e:
                errors.append({"index": i, "error": str(e)})

    elif data.item_type == "restaurant":
        from app.schemas.cuisine import CreateRestaurantRequest
        from app.services import cuisine_service
        for i, item in enumerate(data.items):
            try:
                req = CreateRestaurantRequest(**item)
                await cuisine_service.create_restaurant(req, owner_id=owner_id)
                imported += 1
            except Exception as e:
                errors.append({"index": i, "error": str(e)})

    return {"imported": imported, "total": len(data.items), "errors": errors}
