from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.booking import BookingStatus
from app.schemas.auth import TokenPayload
from app.schemas.booking import (
    CreateBookingRequest,
    BookingResponse,
    CancelBookingRequest,
    InvoiceResponse,
)
from app.services import booking_service
from app.services.booking_provider_resolver import is_authorized_for_establishment

router = APIRouter(prefix="/bookings", tags=["Réservation et billetterie"])

PROVIDER_ITEM_TYPES = {"hotel", "restaurant", "transport", "product"}


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    data: CreateBookingRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Réserver : hôtels, activités, guides, restaurants, transport, événements, visites (§33)."""
    return await booking_service.create_booking(data, customer_id=current_user.sub)


@router.get("/me", response_model=list)
async def list_my_bookings(
    status_filter: Optional[BookingStatus] = None,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Historique des achats et réservations."""
    return await booking_service.list_my_bookings(current_user.sub, status_filter)


@router.get("/reference/{reference}", response_model=BookingResponse)
async def get_booking_by_reference(reference: str):
    """Présenter/valider le ticket QR Code."""
    return await booking_service.get_booking_by_reference(reference)


@router.get("/provider/received", response_model=list)
async def list_received_bookings(
    item_type: str = Query(..., description="hotel, restaurant, transport ou product"),
    item_id: str = Query(...),
    status_filter: Optional[BookingStatus] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Provider) Réservations reçues sur un établissement précis qu'il possède,
    avec le nom/téléphone du client."""
    if item_type not in PROVIDER_ITEM_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type d'activité invalide")
    if current_user.role != UserRole.ADMIN:
        if not await is_authorized_for_establishment(item_type, item_id, current_user.sub):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cet établissement ne vous appartient pas")
    return await booking_service.list_provider_bookings(item_type, item_id, status_filter)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Détail d'une réservation, avec statut."""
    return await booking_service.get_booking(booking_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN)


@router.post("/{booking_id}/confirm", response_model=BookingResponse)
async def confirm_booking(
    booking_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.PROVIDER, UserRole.GUIDE)),
):
    """(Admin, ou le prestataire propriétaire de l'item) Confirmer une réservation."""
    return await booking_service.confirm_booking(
        booking_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: str,
    data: CancelBookingRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Annuler selon les conditions."""
    return await booking_service.cancel_booking(
        booking_id, data.reason, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )


@router.post("/{booking_id}/refund", response_model=BookingResponse)
async def request_refund(booking_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Demander un remboursement selon les conditions."""
    return await booking_service.request_refund(
        booking_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )


@router.get("/{booking_id}/invoice", response_model=InvoiceResponse)
async def get_invoice(booking_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Facture / reçu numérique."""
    return await booking_service.get_or_create_invoice(
        booking_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )
