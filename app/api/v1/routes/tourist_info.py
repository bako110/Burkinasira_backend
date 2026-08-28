from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import require_role
from app.models.user import UserRole
from app.models.tourist_info import TravelInfoCategory
from app.schemas.auth import TokenPayload
from app.schemas.tourist_info import (
    CreateTravelInfoRequest,
    UpdateTravelInfoRequest,
    TravelInfoResponse,
    CreateDiplomaticContactRequest,
    UpdateDiplomaticContactRequest,
    DiplomaticContactResponse,
)
from app.services import tourist_info_service

router = APIRouter(prefix="/tourist-info", tags=["Administrations et formalités du voyage"])


@router.get("/travel-info", response_model=list)
async def list_travel_info(category: Optional[TravelInfoCategory] = None):
    """Passeport/visa, formalités entrée-sortie, douanes, permis touristiques (§15)."""
    return await tourist_info_service.list_travel_info(category)


@router.get("/travel-info/{info_id}", response_model=TravelInfoResponse)
async def get_travel_info(info_id: str):
    """Détail d'une information administrative."""
    return await tourist_info_service.get_travel_info(info_id)


@router.post("/travel-info", response_model=TravelInfoResponse, status_code=status.HTTP_201_CREATED)
async def create_travel_info(
    data: CreateTravelInfoRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Publier une information administrative officielle."""
    return await tourist_info_service.create_travel_info(data)


@router.patch("/travel-info/{info_id}", response_model=TravelInfoResponse)
async def update_travel_info(
    info_id: str,
    data: UpdateTravelInfoRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Mettre à jour une information administrative."""
    return await tourist_info_service.update_travel_info(info_id, data)


@router.delete("/travel-info/{info_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_travel_info(
    info_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer une information administrative."""
    await tourist_info_service.delete_travel_info(info_id)


@router.get("/diplomatic-contacts", response_model=list)
async def list_diplomatic_contacts(country: Optional[str] = None):
    """Contacts des représentations diplomatiques et consulaires (§15)."""
    return await tourist_info_service.list_diplomatic_contacts(country)


@router.post("/diplomatic-contacts", response_model=DiplomaticContactResponse, status_code=status.HTTP_201_CREATED)
async def create_diplomatic_contact(
    data: CreateDiplomaticContactRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Ajouter un contact diplomatique."""
    return await tourist_info_service.create_diplomatic_contact(data)


@router.patch("/diplomatic-contacts/{contact_id}", response_model=DiplomaticContactResponse)
async def update_diplomatic_contact(
    contact_id: str,
    data: UpdateDiplomaticContactRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Mettre à jour un contact diplomatique."""
    return await tourist_info_service.update_diplomatic_contact(contact_id, data)


@router.delete("/diplomatic-contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_diplomatic_contact(
    contact_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un contact diplomatique."""
    await tourist_info_service.delete_diplomatic_contact(contact_id)
