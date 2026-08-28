from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.destination import DestinationCategory
from app.schemas.auth import TokenPayload
from app.schemas.destination import (
    CreateDestinationRequest,
    UpdateDestinationRequest,
    DestinationDetail,
    DestinationListResponse,
)
from app.services import destination_service

router = APIRouter(prefix="/destinations", tags=["Explorer / Destinations"])


@router.get("", response_model=DestinationListResponse)
async def list_destinations(
    category: Optional[DestinationCategory] = None,
    region: Optional[str] = None,
    q: Optional[str] = Query(default=None, description="Recherche texte (nom, description, ville)"),
    min_rating: Optional[float] = Query(default=None, ge=0, le=5),
    near_lat: Optional[float] = Query(default=None, description="Latitude pour recherche par proximité"),
    near_lng: Optional[float] = Query(default=None, description="Longitude pour recherche par proximité"),
    radius_km: Optional[float] = Query(default=None, gt=0, description="Rayon de recherche en km"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Explorer le Burkina Faso : carte/liste filtrable par catégorie, région, distance, note (§3)."""
    return await destination_service.list_destinations(
        category=category,
        region=region,
        q=q,
        min_rating=min_rating,
        near_lat=near_lat,
        near_lng=near_lng,
        radius_km=radius_km,
        page=page,
        page_size=page_size,
    )


@router.get("/{destination_id}", response_model=DestinationDetail)
async def get_destination(destination_id: str):
    """Fiche complète d'un lieu (§4)."""
    return await destination_service.get_destination(destination_id)


@router.get("/slug/{slug}", response_model=DestinationDetail)
async def get_destination_by_slug(slug: str):
    """Fiche complète d'un lieu par slug (URL lisible)."""
    return await destination_service.get_destination_by_slug(slug)


@router.get("/{destination_id}/nearby", response_model=list)
async def get_nearby(destination_id: str, radius_km: float = 5.0, limit: int = 10):
    """Lieux et services à proximité d'un lieu (§4)."""
    return await destination_service.get_nearby_destinations(destination_id, radius_km, limit)


@router.post("", response_model=DestinationDetail, status_code=status.HTTP_201_CREATED)
async def create_destination(
    data: CreateDestinationRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Créer une fiche lieu."""
    return await destination_service.create_destination(data, created_by=current_user.sub)


@router.patch("/{destination_id}", response_model=DestinationDetail)
async def update_destination(
    destination_id: str,
    data: UpdateDestinationRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour une fiche lieu."""
    return await destination_service.update_destination(destination_id, data)


@router.delete("/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_destination(
    destination_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer une fiche lieu."""
    await destination_service.delete_destination(destination_id)
