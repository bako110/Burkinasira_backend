from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, get_current_user_optional, require_role
from app.models.user import UserRole
from app.models.mobility import TransportType
from app.schemas.auth import TokenPayload
from app.schemas.mobility import (
    CreateTransportProviderRequest,
    UpdateTransportProviderRequest,
    TransportProviderDetail,
    TransportProviderListResponse,
    CreateTripRequest,
    TripRequestResponse,
    UpdateTripStatusRequest,
)
from app.services import mobility_service

router = APIRouter(prefix="/mobility", tags=["Transport et mobilité — BurkinaSira Mobility"])


@router.get("/providers", response_model=TransportProviderListResponse)
async def list_providers(
    type: Optional[TransportType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    include_all_statuses: bool = False,
    near_lat: Optional[float] = Query(default=None, description="Latitude pour recherche par proximité"),
    near_lng: Optional[float] = Query(default=None, description="Longitude pour recherche par proximité"),
    radius_km: Optional[float] = Query(default=None, gt=0, description="Rayon de recherche en km"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: Optional[TokenPayload] = Depends(get_current_user_optional),
):
    """Rechercher un trajet : taxis/VTC, chauffeurs privés, location, transferts aéroport (§11)."""
    is_admin = current_user is not None and current_user.role in (UserRole.ADMIN, UserRole.MODERATOR)
    return await mobility_service.list_providers(
        type=type, region=region, province=province,
        near_lat=near_lat, near_lng=near_lng, radius_km=radius_km,
        page=page, page_size=page_size,
        include_all_statuses=include_all_statuses and is_admin,
    )


@router.get("/providers/me/list", response_model=list)
async def list_my_providers(
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Provider) Liste de mes services de transport, tous statuts confondus."""
    return await mobility_service.list_my_providers(current_user.sub)


@router.get("/providers/{provider_id}", response_model=TransportProviderDetail)
async def get_provider(provider_id: str):
    """Détail d'un prestataire de transport."""
    return await mobility_service.get_provider(provider_id)


@router.post("/providers", response_model=TransportProviderDetail, status_code=status.HTTP_201_CREATED)
async def create_provider(
    data: CreateTransportProviderRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Provider/Admin/Moderateur) Référencer un service de transport. Reste en attente (pending)
    tant que le compte n'est pas vérifié par un admin."""
    return await mobility_service.create_provider(data, owner_id=current_user.sub)


@router.patch("/providers/{provider_id}", response_model=TransportProviderDetail)
async def update_provider(
    provider_id: str,
    data: UpdateTransportProviderRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Owner/Admin) Mettre à jour un prestataire de transport."""
    return await mobility_service.update_provider(
        provider_id, data, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Owner/Admin) Supprimer un prestataire de transport."""
    await mobility_service.delete_provider(
        provider_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )


# Left ADMIN-only: verification/trust status change on a provider account, not content management.
@router.post("/providers/{provider_id}/verify", response_model=TransportProviderDetail)
async def verify_provider(
    provider_id: str,
    is_verified: bool = True,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Vérifier un prestataire de transport (§37)."""
    return await mobility_service.set_verification_status(provider_id, is_verified)


@router.post("/trips", response_model=TripRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_trip(
    data: CreateTripRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Réserver un trajet."""
    return await mobility_service.create_trip_request(data, passenger_id=current_user.sub)


@router.get("/trips/me", response_model=list)
async def list_my_trips(current_user: TokenPayload = Depends(get_current_user)):
    """Suivre ses réservations de trajet."""
    return await mobility_service.list_my_trips(current_user.sub)


@router.get("/trips/{trip_id}", response_model=TripRequestResponse)
async def get_trip(trip_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Suivre une réservation de trajet spécifique."""
    return await mobility_service.get_trip_request(trip_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN)


@router.patch("/trips/{trip_id}/status", response_model=TripRequestResponse)
async def update_trip_status(
    trip_id: str,
    data: UpdateTripStatusRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Mettre à jour le statut d'un trajet (passager, prestataire ou admin)."""
    return await mobility_service.update_trip_status(
        trip_id, data.status, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )
