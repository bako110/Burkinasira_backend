from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import require_role
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.schemas.pro_workspace import (
    ProDashboardResponse,
    CreatePromotionRequest,
    PromotionResponse,
    InviteTeamMemberRequest,
    TeamMemberResponse,
)
from app.services import pro_workspace_service

router = APIRouter(prefix="/pro", tags=["Espace professionnel"])


@router.get("/dashboard", response_model=ProDashboardResponse)
async def get_dashboard(
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """Tableau de bord pro : réservations, revenus, statistiques (§35)."""
    return await pro_workspace_service.get_dashboard(current_user.sub)


@router.post("/promotions", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
async def create_promotion(
    data: CreatePromotionRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """Créer une promotion sur une offre."""
    return await pro_workspace_service.create_promotion(data, provider_id=current_user.sub)


@router.get("/promotions", response_model=list)
async def list_my_promotions(
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """Ses promotions."""
    return await pro_workspace_service.list_my_promotions(current_user.sub)


@router.post("/team", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_team_member(
    data: InviteTeamMemberRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """Gérer son équipe : inviter un membre."""
    return await pro_workspace_service.invite_team_member(data, provider_id=current_user.sub)


@router.get("/team", response_model=list)
async def list_team_members(
    establishment_type: Optional[str] = Query(default=None),
    establishment_id: Optional[str] = Query(default=None),
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """Liste des membres d'équipe. Filtrée à un établissement précis si fourni."""
    return await pro_workspace_service.list_team_members(current_user.sub, establishment_type, establishment_id)


@router.delete("/team/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    member_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """Retirer un membre d'équipe."""
    await pro_workspace_service.remove_team_member(member_id, current_user.sub)
