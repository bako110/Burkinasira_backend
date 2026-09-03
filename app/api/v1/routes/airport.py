from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import require_role
from app.models.user import UserRole
from app.models.airport import AirportInfoCategory
from app.schemas.auth import TokenPayload
from app.schemas.airport import (
    CreateAirportRequest,
    UpdateAirportRequest,
    AirportResponse,
    CreateAirportInfoRequest,
    UpdateAirportInfoRequest,
    AirportInfoResponse,
    CreateBorderCrossingRequest,
    UpdateBorderCrossingRequest,
    BorderCrossingResponse,
)
from app.services import airport_service

router = APIRouter(prefix="/airport", tags=["Aéroport, frontières et arrivée"])


@router.get("/airports", response_model=list)
async def list_airports():
    """Liste des aéroports référencés (§16)."""
    return await airport_service.list_airports()


@router.get("/airports/{airport_id}", response_model=AirportResponse)
async def get_airport(airport_id: str):
    """Détail d'un aéroport."""
    return await airport_service.get_airport(airport_id)


@router.post("/airports", response_model=AirportResponse, status_code=status.HTTP_201_CREATED)
async def create_airport(
    data: CreateAirportRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Ajouter un aéroport."""
    return await airport_service.create_airport(data)


@router.patch("/airports/{airport_id}", response_model=AirportResponse)
async def update_airport(
    airport_id: str,
    data: UpdateAirportRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour un aéroport."""
    return await airport_service.update_airport(airport_id, data)


@router.delete("/airports/{airport_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_airport(
    airport_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un aéroport."""
    await airport_service.delete_airport(airport_id)


@router.get("/airports/{airport_id}/info", response_model=list)
async def list_airport_info(airport_id: str, category: Optional[AirportInfoCategory] = None):
    """Infos aéroportuaires : horaires, transport, change, connectivité, formalités, contacts (§16)."""
    return await airport_service.list_airport_info(airport_id, category)


@router.post("/airports/{airport_id}/info", response_model=AirportInfoResponse, status_code=status.HTTP_201_CREATED)
async def add_airport_info(
    airport_id: str,
    data: CreateAirportInfoRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Ajouter un bloc d'information pour un aéroport."""
    return await airport_service.add_airport_info(airport_id, data)


@router.patch("/info/{info_id}", response_model=AirportInfoResponse)
async def update_airport_info(
    info_id: str,
    data: UpdateAirportInfoRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour un bloc d'information aéroport."""
    return await airport_service.update_airport_info(info_id, data)


@router.delete("/info/{info_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_airport_info(
    info_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un bloc d'information aéroport."""
    await airport_service.delete_airport_info(info_id)


@router.get("/borders", response_model=list)
async def list_border_crossings(region: Optional[str] = None):
    """Points de sortie et frontières publiés (§16)."""
    return await airport_service.list_border_crossings(region)


@router.post("/borders", response_model=BorderCrossingResponse, status_code=status.HTTP_201_CREATED)
async def create_border_crossing(
    data: CreateBorderCrossingRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Ajouter un point de frontière."""
    return await airport_service.create_border_crossing(data)


@router.get("/borders/{border_id}", response_model=BorderCrossingResponse)
async def get_border_crossing(border_id: str):
    """Détail d'un point de frontière."""
    return await airport_service.get_border_crossing(border_id)


@router.patch("/borders/{border_id}", response_model=BorderCrossingResponse)
async def update_border_crossing(
    border_id: str,
    data: UpdateBorderCrossingRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour un point de frontière."""
    return await airport_service.update_border_crossing(border_id, data)


@router.delete("/borders/{border_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_border_crossing(
    border_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un point de frontière."""
    await airport_service.delete_border_crossing(border_id)
