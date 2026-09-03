from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.schemas.privacy import (
    SetConsentRequest,
    ConsentResponse,
    DataExportResponse,
    CreateRetentionPolicyRequest,
    RetentionPolicyResponse,
)
from app.services import privacy_service

router = APIRouter(prefix="/privacy", tags=["Confidentialité et gouvernance des données"])


@router.get("/consents/me", response_model=list)
async def list_my_consents(current_user: TokenPayload = Depends(get_current_user)):
    """Gérer ses données personnelles et ses préférences de consentement (§47)."""
    return await privacy_service.list_my_consents(current_user.sub)


@router.put("/consents/me", response_model=ConsentResponse)
async def set_consent(
    data: SetConsentRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Donner ou retirer son consentement (analytics, marketing, localisation, recommandations)."""
    return await privacy_service.set_consent(data, current_user.sub)


@router.get("/export/me", response_model=DataExportResponse)
async def export_my_data(current_user: TokenPayload = Depends(get_current_user)):
    """Exporter ses données personnelles."""
    return await privacy_service.export_my_data(current_user.sub)


@router.get("/retention-policies", response_model=list)
async def list_retention_policies():
    """Politique de conservation des données, publique."""
    return await privacy_service.list_retention_policies()


# Left ADMIN-only: data retention/compliance policy configuration, needs a product decision before opening to moderators.
@router.put("/retention-policies", response_model=RetentionPolicyResponse)
async def set_retention_policy(
    data: CreateRetentionPolicyRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Définir la politique de conservation d'une catégorie de données."""
    return await privacy_service.set_retention_policy(data)


@router.get("/action-log", response_model=list)
async def list_privacy_log(
    user_id: Optional[str] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Journalisation des actions sensibles liées à la vie privée."""
    return await privacy_service.list_privacy_log(user_id)
