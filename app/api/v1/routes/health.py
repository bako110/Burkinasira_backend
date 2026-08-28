from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.health import HealthFacilityType
from app.schemas.auth import TokenPayload
from app.schemas.health import (
    CreateHealthFacilityRequest,
    UpdateHealthFacilityRequest,
    HealthFacilityDetail,
    HealthFacilityListResponse,
)
from app.services import health_service

router = APIRouter(prefix="/health-facilities", tags=["Santé"])


@router.get("", response_model=HealthFacilityListResponse)
async def list_health_facilities(
    type: Optional[HealthFacilityType] = None,
    region: Optional[str] = None,
    on_duty_only: bool = Query(default=False, description="Pharmacies de garde uniquement"),
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Pharmacies, hôpitaux, cliniques, laboratoires... par distance/horaires/services (§9)."""
    return await health_service.list_health_facilities(
        type=type, region=region, on_duty_only=on_duty_only,
        near_lat=near_lat, near_lng=near_lng, radius_km=radius_km,
        page=page, page_size=page_size,
    )


@router.get("/favorites", response_model=list)
async def list_my_favorites(current_user: TokenPayload = Depends(get_current_user)):
    """Établissements de santé enregistrés en favori."""
    return await health_service.list_favorites(current_user.sub)


@router.get("/{facility_id}", response_model=HealthFacilityDetail)
async def get_health_facility(facility_id: str):
    """Fiche détaillée : horaires, services, date/source de mise à jour."""
    return await health_service.get_health_facility(facility_id)


@router.post("/{facility_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def add_favorite(facility_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Enregistrer un établissement en favori."""
    await health_service.add_favorite(current_user.sub, facility_id)


@router.delete("/{facility_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(facility_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Retirer un établissement des favoris."""
    await health_service.remove_favorite(current_user.sub, facility_id)


@router.post("", response_model=HealthFacilityDetail, status_code=status.HTTP_201_CREATED)
async def create_health_facility(
    data: CreateHealthFacilityRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Ajouter un établissement de santé."""
    return await health_service.create_health_facility(data, created_by=current_user.sub)


@router.patch("/{facility_id}", response_model=HealthFacilityDetail)
async def update_health_facility(
    facility_id: str,
    data: UpdateHealthFacilityRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour un établissement (horaires, statut garde, etc.)."""
    return await health_service.update_health_facility(facility_id, data)


@router.delete("/{facility_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_facility(
    facility_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un établissement de santé."""
    await health_service.delete_health_facility(facility_id)
