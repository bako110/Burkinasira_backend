from fastapi import APIRouter, Depends, status
from app.core.security import require_role
from app.models.user import UserRole
from app.models.integration import ConnectorType
from app.schemas.auth import TokenPayload
from app.schemas.integration import (
    UpdateConnectorRequest,
    ConnectorResponse,
    CreateWebhookRequest,
    WebhookResponse,
    ImportDataRequest,
)
from app.services import integration_service

router = APIRouter(prefix="/integrations", tags=["API et intégrations"])


@router.get("/connectors", response_model=list)
async def list_connectors(current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))):
    """Connecteurs disponibles : cartographie, météo, paiement, notifications, SMS/WhatsApp, billetterie... (§46)."""
    return await integration_service.list_connectors()


@router.put("/connectors/{connector_type}", response_model=ConnectorResponse)
async def upsert_connector(
    connector_type: ConnectorType,
    data: UpdateConnectorRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin/Moderateur) Configurer un connecteur."""
    return await integration_service.upsert_connector(connector_type, data, actor_id=current_user.sub)


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: CreateWebhookRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR, UserRole.PROVIDER)),
):
    """Créer un webhook pour les réservations et paiements."""
    return await integration_service.create_webhook(data, owner_id=current_user.sub)


@router.get("/webhooks", response_model=list)
async def list_my_webhooks(
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR, UserRole.PROVIDER)),
):
    """Ses webhooks configurés."""
    return await integration_service.list_my_webhooks(current_user.sub)


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.PROVIDER)),
):
    """Supprimer un webhook."""
    await integration_service.delete_webhook(webhook_id, current_user.sub)


@router.post("/import")
async def import_data(
    data: ImportDataRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Pro) Importer des données via le système d'import."""
    return await integration_service.import_data(data, owner_id=current_user.sub)
