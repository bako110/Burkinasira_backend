from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.schemas.emergency import (
    CreateEmergencyContactRequest,
    UpdateEmergencyContactRequest,
    EmergencyContactResponse,
    TriggerSOSRequest,
    SOSAlertResponse,
)
from app.services import emergency_service

router = APIRouter(prefix="/emergency-services", tags=["Urgences et sécurité"])


@router.get("/contacts", response_model=list)
async def list_emergency_contacts(region: Optional[str] = None):
    """Numéros officiels : Police, Pompiers, Gendarmerie, SAMU (§10)."""
    return await emergency_service.list_contacts(region)


@router.post("/contacts", response_model=EmergencyContactResponse, status_code=status.HTTP_201_CREATED)
async def create_emergency_contact(
    data: CreateEmergencyContactRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Ajouter un numéro officiel."""
    return await emergency_service.create_contact(data)


@router.patch("/contacts/{contact_id}", response_model=EmergencyContactResponse)
async def update_emergency_contact(
    contact_id: str,
    data: UpdateEmergencyContactRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour un numéro officiel."""
    return await emergency_service.update_contact(contact_id, data)


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_emergency_contact(
    contact_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un numéro officiel."""
    await emergency_service.delete_contact(contact_id)


@router.post("/sos", response_model=SOSAlertResponse, status_code=status.HTTP_201_CREATED)
async def trigger_sos(
    data: TriggerSOSRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Déclencher le bouton SOS : partage de localisation, contact de confiance, numéros d'urgence (§10)."""
    return await emergency_service.trigger_sos(data, current_user.sub)
