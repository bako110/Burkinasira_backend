from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.hotel import AccommodationType
from app.schemas.auth import TokenPayload
from app.schemas.hotel import (
    CreateHotelRequest,
    UpdateHotelRequest,
    HotelDetail,
    HotelListResponse,
    AvailabilityCheckRequest,
    AvailabilityCheckResponse,
)
from app.services import hotel_service

router = APIRouter(prefix="/hotels", tags=["Hébergements"])


@router.get("", response_model=HotelListResponse)
async def list_hotels(
    type: Optional[AccommodationType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    city: Optional[str] = None,
    max_price: Optional[float] = None,
    amenity: Optional[str] = None,
    q: Optional[str] = Query(default=None, description="Recherche texte (nom, description)"),
    near_lat: Optional[float] = Query(default=None, description="Latitude pour recherche par proximité"),
    near_lng: Optional[float] = Query(default=None, description="Longitude pour recherche par proximité"),
    radius_km: Optional[float] = Query(default=None, gt=0, description="Rayon de recherche en km"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Rechercher / filtrer des hébergements (§7)."""
    return await hotel_service.list_hotels(
        type=type, region=region, province=province, city=city, max_price=max_price,
        amenity=amenity, q=q, near_lat=near_lat, near_lng=near_lng, radius_km=radius_km,
        page=page, page_size=page_size,
    )


@router.get("/me/list", response_model=list)
async def list_my_hotels(
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Provider) Liste de mes hébergements, tous statuts confondus."""
    return await hotel_service.list_my_hotels(current_user.sub)


@router.get("/{hotel_id}", response_model=HotelDetail)
async def get_hotel(hotel_id: str):
    """Fiche détaillée d'un hébergement."""
    return await hotel_service.get_hotel(hotel_id)


@router.post("/{hotel_id}/availability", response_model=AvailabilityCheckResponse)
async def check_availability(hotel_id: str, data: AvailabilityCheckRequest):
    """Consulter les disponibilités pour des dates arrivée/départ données (§7)."""
    return await hotel_service.check_availability(hotel_id, data)


@router.post("", response_model=HotelDetail, status_code=status.HTTP_201_CREATED)
async def create_hotel(
    data: CreateHotelRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Provider/Admin/Moderateur) Ajouter un hébergement. Publié directement si le compte est déjà
    vérifié, sinon enregistré en brouillon en attendant l'approbation admin."""
    return await hotel_service.create_hotel(
        data, owner_id=current_user.sub, is_admin=current_user.role in (UserRole.ADMIN, UserRole.MODERATOR)
    )


@router.patch("/{hotel_id}", response_model=HotelDetail)
async def update_hotel(
    hotel_id: str,
    data: UpdateHotelRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Owner/Admin) Mettre à jour un hébergement."""
    return await hotel_service.update_hotel(
        hotel_id, data, current_user.sub, is_admin=current_user.role in (UserRole.ADMIN, UserRole.MODERATOR)
    )


@router.delete("/{hotel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hotel(
    hotel_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Owner/Admin) Supprimer un hébergement."""
    await hotel_service.delete_hotel(
        hotel_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )
