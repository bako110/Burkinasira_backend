from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.integration import ConnectorType, ConnectorStatus, WebhookEventType


class UpdateConnectorRequest(BaseModel):
    provider_name: str = Field(..., min_length=2, max_length=100)
    status: ConnectorStatus
    config_notes: Optional[str] = None


class ConnectorResponse(BaseModel):
    id: str
    type: ConnectorType
    provider_name: str
    status: ConnectorStatus
    config_notes: Optional[str] = None
    updated_at: datetime


class CreateWebhookRequest(BaseModel):
    event_type: WebhookEventType
    target_url: str


class WebhookResponse(BaseModel):
    id: str
    owner_id: str
    event_type: WebhookEventType
    target_url: str
    is_active: bool
    created_at: datetime


class ImportDataRequest(BaseModel):
    item_type: str
    items: list  # liste de dicts prêts à insérer, validés par le service cible
