from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.schemas.guide import AvailabilitySlotRequest, AvailabilitySlotResponse
from app.schemas.messaging import ConversationResponse
from app.services import guide_availability_service, guide_service

router = APIRouter(tags=["Disponibilités des guides"])


@router.get("/{guide_id}", response_model=list[AvailabilitySlotResponse])
async def list_guide_availability(
    guide_id: str,
    date: Optional[str] = None,
    available_only: bool = False,
):
    """Consulter les créneaux de disponibilité d'un guide, pour réservation (§6, §33)."""
    return await guide_availability_service.list_slots(guide_id, date=date, available_only=available_only)


@router.post("/me", response_model=AvailabilitySlotResponse, status_code=status.HTTP_201_CREATED)
async def add_my_availability(
    data: AvailabilitySlotRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.GUIDE, UserRole.ADMIN)),
):
    """(Guide) Ajouter un créneau de disponibilité."""
    guide = await guide_service.get_guide_by_user_id(current_user.sub)
    return await guide_availability_service.add_slot(guide.id, data)


@router.post("/{slot_id}/contact", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def contact_guide_about_slot(
    slot_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Touriste) Contacter le guide au sujet d'un créneau choisi, sans réserver."""
    return await guide_availability_service.contact_guide_about_slot(slot_id, tourist_id=current_user.sub)


@router.delete("/me/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_availability(
    slot_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.GUIDE, UserRole.ADMIN)),
):
    """(Guide) Supprimer un créneau non réservé."""
    guide = await guide_service.get_guide_by_user_id(current_user.sub)
    await guide_availability_service.delete_slot(slot_id, guide.id)
