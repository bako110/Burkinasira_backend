from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.event import EventCategory
from app.schemas.auth import TokenPayload
from app.schemas.event import (
    CreateEventRequest,
    UpdateEventRequest,
    EventDetail,
    EventListResponse,
)
from app.services import event_service

router = APIRouter(prefix="/events", tags=["Événements et calendrier national"])


@router.get("", response_model=EventListResponse)
async def list_events(
    category: Optional[EventCategory] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    upcoming_only: bool = Query(default=True, description="Uniquement les événements à venir"),
    q: Optional[str] = Query(default=None, description="Recherche texte (titre, description)"),
    near_lat: Optional[float] = Query(default=None, description="Latitude pour recherche par proximité"),
    near_lng: Optional[float] = Query(default=None, description="Longitude pour recherche par proximité"),
    radius_km: Optional[float] = Query(default=None, gt=0, description="Rayon de recherche en km"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Rechercher / filtrer un événement (§17)."""
    return await event_service.list_events(
        category=category, region=region, province=province, upcoming_only=upcoming_only,
        q=q, near_lat=near_lat, near_lng=near_lng, radius_km=radius_km,
        page=page, page_size=page_size,
    )


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(event_id: str):
    """Détail d'un événement : programme, localisation, transport/hébergement liés."""
    return await event_service.get_event(event_id)


@router.post("", response_model=EventDetail, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: CreateEventRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Provider/Admin/Moderateur) Publier un événement."""
    return await event_service.create_event(data, organizer_id=current_user.sub)


@router.patch("/{event_id}", response_model=EventDetail)
async def update_event(
    event_id: str,
    data: UpdateEventRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Organisateur/Admin) Mettre à jour un événement."""
    return await event_service.update_event(
        event_id, data, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Organisateur/Admin) Supprimer un événement."""
    await event_service.delete_event(
        event_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )
