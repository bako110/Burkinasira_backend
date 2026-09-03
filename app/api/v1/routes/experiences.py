from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.experience import ExperienceType
from app.schemas.auth import TokenPayload
from app.schemas.experience import (
    CreateExperienceRequest,
    UpdateExperienceRequest,
    ExperienceDetail,
    ExperienceListResponse,
)
from app.services import experience_service, user_service

router = APIRouter(prefix="/experiences", tags=["Expériences communautaires"])


@router.get("", response_model=ExperienceListResponse)
async def list_experiences(
    type: Optional[ExperienceType] = None,
    region: Optional[str] = None,
    q: Optional[str] = Query(default=None, description="Recherche texte (titre, description)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Rechercher / filtrer une expérience humaine ou communautaire (§5)."""
    return await experience_service.list_experiences(
        type=type, region=region, q=q, page=page, page_size=page_size
    )


@router.get("/{experience_id}", response_model=ExperienceDetail)
async def get_experience(experience_id: str):
    """Détail d'une expérience, incluant la répartition des revenus si définie."""
    return await experience_service.get_experience(experience_id)


@router.post("", response_model=ExperienceDetail, status_code=status.HTTP_201_CREATED)
async def create_experience(
    data: CreateExperienceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.GUIDE, UserRole.PROVIDER, UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Guide/Provider/Admin/Moderateur) Publier une expérience communautaire."""
    host = await user_service.get_user_by_id(current_user.sub)
    return await experience_service.create_experience(data, host_id=current_user.sub, host_name=host.full_name)


@router.patch("/{experience_id}", response_model=ExperienceDetail)
async def update_experience(
    experience_id: str,
    data: UpdateExperienceRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Hôte/Admin/Moderateur) Mettre à jour une expérience."""
    return await experience_service.update_experience(
        experience_id, data, current_user.sub, is_admin=current_user.role in (UserRole.ADMIN, UserRole.MODERATOR)
    )


@router.delete("/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(
    experience_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Hôte/Admin) Supprimer une expérience."""
    await experience_service.delete_experience(
        experience_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )
