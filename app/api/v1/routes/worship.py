from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import require_role
from app.models.user import UserRole
from app.models.worship import WorshipPlaceType
from app.schemas.auth import TokenPayload
from app.schemas.worship import (
    CreateWorshipPlaceRequest,
    UpdateWorshipPlaceRequest,
    WorshipPlaceDetail,
    WorshipPlaceListResponse,
)
from app.services import worship_service

router = APIRouter(prefix="/worship-places", tags=["Religion, lieux de culte et services associés"])


@router.get("", response_model=WorshipPlaceListResponse)
async def list_worship_places(
    type: Optional[WorshipPlaceType] = None,
    region: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Mosquées, églises et autres lieux de culte ouverts au public (§21)."""
    return await worship_service.list_worship_places(type=type, region=region, page=page, page_size=page_size)


@router.get("/{place_id}", response_model=WorshipPlaceDetail)
async def get_worship_place(place_id: str):
    """Détail : horaires/événements publics, règles de visite, services à proximité."""
    return await worship_service.get_worship_place(place_id)


@router.post("", response_model=WorshipPlaceDetail, status_code=status.HTTP_201_CREATED)
async def create_worship_place(
    data: CreateWorshipPlaceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Référencer un lieu de culte."""
    return await worship_service.create_worship_place(data)


@router.patch("/{place_id}", response_model=WorshipPlaceDetail)
async def update_worship_place(
    place_id: str,
    data: UpdateWorshipPlaceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour un lieu de culte."""
    return await worship_service.update_worship_place(place_id, data)


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_worship_place(
    place_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un lieu de culte."""
    await worship_service.delete_worship_place(place_id)
