from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import require_role
from app.models.user import UserRole
from app.models.story import CultureContentType
from app.schemas.auth import TokenPayload
from app.schemas.story import (
    CreateCultureContentRequest,
    UpdateCultureContentRequest,
    CultureContentDetail,
    CultureContentListResponse,
    CreateCulturalRouteRequest,
    UpdateCulturalRouteRequest,
    CulturalRouteResponse,
)
from app.services import story_service

router = APIRouter(prefix="/culture", tags=["Culture, patrimoine et mémoire"])


@router.get("/content", response_model=CultureContentListResponse)
async def list_content(
    type: Optional[CultureContentType] = None,
    region: Optional[str] = None,
    q: Optional[str] = Query(default=None, description="Recherche texte (titre, résumé)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Histoire, patrimoine, traditions, contes, musique, guides audio/vidéo (§18)."""
    return await story_service.list_content(type=type, region=region, q=q, page=page, page_size=page_size)


@router.get("/content/{content_id}", response_model=CultureContentDetail)
async def get_content(content_id: str):
    """Détail d'un contenu culturel (texte, guide audio ou vidéo)."""
    return await story_service.get_content(content_id)


@router.post("/content", response_model=CultureContentDetail, status_code=status.HTTP_201_CREATED)
async def create_content(
    data: CreateCultureContentRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Publier un contenu culturel."""
    return await story_service.create_content(data, created_by=current_user.sub)


@router.patch("/content/{content_id}", response_model=CultureContentDetail)
async def update_content(
    content_id: str,
    data: UpdateCultureContentRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour un contenu culturel."""
    return await story_service.update_content(content_id, data)


@router.delete("/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un contenu culturel."""
    await story_service.delete_content(content_id)


@router.get("/routes", response_model=list)
async def list_routes(region: Optional[str] = None):
    """Parcours culturels disponibles (§18)."""
    return await story_service.list_routes(region)


@router.get("/routes/{route_id}", response_model=CulturalRouteResponse)
async def get_route(route_id: str):
    """Suivre un parcours culturel : étapes lieux + contenus."""
    return await story_service.get_route(route_id)


@router.post("/routes", response_model=CulturalRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_route(
    data: CreateCulturalRouteRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Créer un parcours culturel."""
    return await story_service.create_route(data, created_by=current_user.sub)


@router.patch("/routes/{route_id}", response_model=CulturalRouteResponse)
async def update_route(
    route_id: str,
    data: UpdateCulturalRouteRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour un parcours culturel."""
    return await story_service.update_route(route_id, data)


@router.delete("/routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route(
    route_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un parcours culturel."""
    await story_service.delete_route(route_id)
