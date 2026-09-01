from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user
from app.schemas.auth import TokenPayload
from app.schemas.trip import (
    CreateTripRequest,
    UpdateTripRequest,
    TripDetail,
    AddTripDayItemRequest,
    RemoveTripDayItemRequest,
    ShareTripRequest,
)
from app.services import trip_service

router = APIRouter(prefix="/trips", tags=["Itinéraire et planification"])


@router.post("", response_model=TripDetail, status_code=status.HTTP_201_CREATED)
async def create_trip(
    data: CreateTripRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Créer un voyage par budget/durée/région/thème (§25)."""
    return await trip_service.create_trip(data, owner_id=current_user.sub)


@router.get("/me", response_model=list)
async def list_my_trips(current_user: TokenPayload = Depends(get_current_user)):
    """Liste des réservations/voyages de l'utilisateur (propriétaire ou collaborateur)."""
    return await trip_service.list_my_trips(current_user.sub)


@router.get("/{trip_id}", response_model=TripDetail)
async def get_trip(trip_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Détail d'un voyage : calendrier jour par jour, budget prévisionnel."""
    real_id = await trip_service.resolve_trip_id(trip_id)
    return await trip_service.get_trip(real_id, current_user.sub)


@router.patch("/{trip_id}", response_model=TripDetail)
async def update_trip(
    trip_id: str,
    data: UpdateTripRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Mettre à jour un voyage."""
    real_id = await trip_service.resolve_trip_id(trip_id)
    return await trip_service.update_trip(real_id, data, current_user.sub)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(trip_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Supprimer un voyage (créateur uniquement)."""
    real_id = await trip_service.resolve_trip_id(trip_id)
    await trip_service.delete_trip(real_id, current_user.sub)


@router.post("/{trip_id}/days/items", response_model=TripDetail)
async def add_day_item(
    trip_id: str,
    data: AddTripDayItemRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Ajouter un élément au calendrier jour par jour."""
    real_id = await trip_service.resolve_trip_id(trip_id)
    return await trip_service.add_day_item(real_id, data, current_user.sub)


@router.delete("/{trip_id}/days/items", response_model=TripDetail)
async def remove_day_item(
    trip_id: str,
    data: RemoveTripDayItemRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Retirer un élément du calendrier jour par jour."""
    real_id = await trip_service.resolve_trip_id(trip_id)
    return await trip_service.remove_day_item(real_id, data, current_user.sub)


@router.post("/{trip_id}/bookings/{booking_id}", response_model=TripDetail)
async def link_booking(
    trip_id: str,
    booking_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Lier une réservation existante au voyage."""
    real_id = await trip_service.resolve_trip_id(trip_id)
    return await trip_service.link_booking(real_id, booking_id, current_user.sub)


@router.post("/{trip_id}/share", response_model=TripDetail)
async def share_trip(
    trip_id: str,
    data: ShareTripRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Partager le voyage avec un accompagnateur (§25)."""
    real_id = await trip_service.resolve_trip_id(trip_id)
    return await trip_service.share_trip(real_id, data, current_user.sub)
