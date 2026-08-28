from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.impact import ImpactInitiativeCategory
from app.schemas.auth import TokenPayload
from app.schemas.impact import (
    CreateInitiativeRequest,
    UpdateInitiativeRequest,
    InitiativeResponse,
    CreateIndicatorRequest,
    IndicatorResponse,
    SupportInitiativeRequest,
)
from app.services import impact_service

router = APIRouter(prefix="/impact", tags=["Tourisme responsable et impact local"])


@router.get("/initiatives", response_model=list)
async def list_initiatives(
    category: Optional[ImpactInitiativeCategory] = None,
    region: Optional[str] = None,
):
    """Initiatives locales mises en avant (§38)."""
    return await impact_service.list_initiatives(category=category, region=region)


@router.get("/initiatives/{initiative_id}", response_model=InitiativeResponse)
async def get_initiative(initiative_id: str):
    """Détail d'une initiative."""
    return await impact_service.get_initiative(initiative_id)


@router.post("/initiatives", response_model=InitiativeResponse, status_code=status.HTTP_201_CREATED)
async def create_initiative(
    data: CreateInitiativeRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Publier une initiative locale."""
    return await impact_service.create_initiative(data, created_by=current_user.sub)


@router.patch("/initiatives/{initiative_id}", response_model=InitiativeResponse)
async def update_initiative(
    initiative_id: str,
    data: UpdateInitiativeRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour une initiative, la vérifier."""
    return await impact_service.update_initiative(initiative_id, data)


@router.post("/initiatives/{initiative_id}/support", response_model=InitiativeResponse)
async def support_initiative(
    initiative_id: str,
    data: SupportInitiativeRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Soutenir un projet communautaire vérifié."""
    return await impact_service.support_initiative(initiative_id, data, supporter_id=current_user.sub)


@router.delete("/initiatives/{initiative_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_initiative(
    initiative_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer une initiative."""
    await impact_service.delete_initiative(initiative_id)


@router.get("/indicators", response_model=list)
async def list_indicators():
    """Indicateurs d'impact global."""
    return await impact_service.list_indicators()


@router.post("/indicators", response_model=IndicatorResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_indicator(
    data: CreateIndicatorRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Créer/mettre à jour un indicateur d'impact."""
    return await impact_service.create_or_update_indicator(data)


@router.delete("/indicators/{indicator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_indicator(
    indicator_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un indicateur d'impact."""
    await impact_service.delete_indicator(indicator_id)
