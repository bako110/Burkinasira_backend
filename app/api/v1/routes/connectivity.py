from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import require_role
from app.models.user import UserRole
from app.models.connectivity import ConnectivityPointType
from app.schemas.auth import TokenPayload
from app.schemas.connectivity import (
    CreateConnectivityPointRequest,
    UpdateConnectivityPointRequest,
    ConnectivityPointDetail,
    ConnectivityPointListResponse,
)
from app.services import connectivity_service

router = APIRouter(prefix="/connectivity", tags=["Connectivité"])


@router.get("", response_model=ConnectivityPointListResponse)
async def list_connectivity_points(
    type: Optional[ConnectivityPointType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    q: Optional[str] = Query(default=None, description="Recherche texte (nom, opérateur, ville, adresse)"),
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Rechercher un point de connectivité à proximité : opérateurs, SIM/eSIM, Wi-Fi, coworking (§14)."""
    return await connectivity_service.list_points(
        type=type, region=region, province=province, q=q, near_lat=near_lat, near_lng=near_lng,
        radius_km=radius_km, page=page, page_size=page_size,
    )


@router.get("/{point_id}", response_model=ConnectivityPointDetail)
async def get_connectivity_point(point_id: str):
    """Détail d'un point de connectivité."""
    return await connectivity_service.get_point(point_id)


@router.post("", response_model=ConnectivityPointDetail, status_code=status.HTTP_201_CREATED)
async def create_connectivity_point(
    data: CreateConnectivityPointRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Référencer un point de connectivité."""
    return await connectivity_service.create_point(data)


@router.patch("/{point_id}", response_model=ConnectivityPointDetail)
async def update_connectivity_point(
    point_id: str,
    data: UpdateConnectivityPointRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour un point de connectivité."""
    return await connectivity_service.update_point(point_id, data)


@router.delete("/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connectivity_point(
    point_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un point de connectivité."""
    await connectivity_service.delete_point(point_id)
