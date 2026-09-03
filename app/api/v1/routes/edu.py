from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.edu import EduOutingType
from app.schemas.auth import TokenPayload
from app.schemas.edu import (
    CreateOutingRequest,
    UpdateOutingRequest,
    OutingResponse,
    CreateEduBookingRequest,
    EduBookingResponse,
    AddEduParticipantRequest,
    EduParticipantResponse,
)
from app.services import edu_service

router = APIRouter(prefix="/edu", tags=["Tourisme éducatif — BurkinaSira Edu"])


@router.get("/outings")
async def list_outings(
    type: Optional[EduOutingType] = None,
    region: Optional[str] = None,
    q: Optional[str] = Query(default=None, description="Recherche texte sur le titre"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Sorties scolaires, visites historiques/culturelles/scientifiques/agricoles/industrielles (§30)."""
    return await edu_service.list_outings(type=type, region=region, q=q, page=page, page_size=page_size)


@router.get("/outings/{outing_id}", response_model=OutingResponse)
async def get_outing(outing_id: str):
    """Détail d'une sortie éducative."""
    return await edu_service.get_outing(outing_id)


@router.post("/outings", response_model=OutingResponse, status_code=status.HTTP_201_CREATED)
async def create_outing(
    data: CreateOutingRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.GUIDE, UserRole.ADMIN)),
):
    """(Provider/Guide/Admin) Publier une sortie éducative."""
    return await edu_service.create_outing(data, organizer_id=current_user.sub)


@router.patch("/outings/{outing_id}", response_model=OutingResponse)
async def update_outing(
    outing_id: str,
    data: UpdateOutingRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Organisateur/Admin) Mettre à jour une sortie éducative."""
    return await edu_service.update_outing(outing_id, data, current_user.sub, is_admin=current_user.role == UserRole.ADMIN)


@router.delete("/outings/{outing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outing(
    outing_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Organisateur/Admin) Supprimer une sortie éducative."""
    await edu_service.delete_outing(outing_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN)


@router.post("/bookings", response_model=EduBookingResponse, status_code=status.HTTP_201_CREATED)
async def book_outing(
    data: CreateEduBookingRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Réserver une sortie ou une visite pour un groupe (§30)."""
    return await edu_service.book_outing(data, booked_by=current_user.sub)


@router.get("/bookings/me", response_model=list)
async def list_my_bookings(current_user: TokenPayload = Depends(get_current_user)):
    """Ses réservations de sorties éducatives."""
    return await edu_service.list_my_bookings(current_user.sub)


@router.post("/bookings/{booking_id}/participants", response_model=EduParticipantResponse, status_code=status.HTTP_201_CREATED)
async def add_participant(
    booking_id: str,
    data: AddEduParticipantRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Gérer les groupes et les participants."""
    return await edu_service.add_participant(booking_id, data, current_user.sub)


@router.get("/bookings/{booking_id}/participants", response_model=list)
async def list_participants(booking_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Liste des participants d'un groupe."""
    return await edu_service.list_participants(booking_id)
