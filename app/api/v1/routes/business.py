from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.business import QuoteRequestStatus
from app.schemas.auth import TokenPayload
from app.schemas.business import (
    CreateQuoteRequest,
    UpdateQuoteRequest,
    QuoteRequestResponse,
    CreateInvoiceRequest,
    InvoiceResponse,
    UpdateInvoiceStatusRequest,
    AddParticipantRequest,
    ParticipantResponse,
)
from app.services import business_service

router = APIRouter(prefix="/business", tags=["Tourisme d'affaires — BurkinaSira Business"])


@router.post("/quotes", response_model=QuoteRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_quote_request(
    data: CreateQuoteRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Demander un devis groupé : séminaires, congrès, team building (§29)."""
    return await business_service.create_quote_request(data, requester_id=current_user.sub)


@router.get("/quotes/me", response_model=list)
async def list_my_quote_requests(current_user: TokenPayload = Depends(get_current_user)):
    """Ses demandes de devis."""
    return await business_service.list_my_quote_requests(current_user.sub)


@router.get("/quotes", response_model=list)
async def list_all_quote_requests(
    status_filter: Optional[QuoteRequestStatus] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.PROVIDER)),
):
    """(Admin/Provider) Toutes les demandes de devis."""
    return await business_service.list_all_quote_requests(status_filter)


@router.get("/quotes/{quote_id}", response_model=QuoteRequestResponse)
async def get_quote_request(quote_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Détail d'une demande de devis."""
    return await business_service.get_quote_request(quote_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN)


@router.patch("/quotes/{quote_id}", response_model=QuoteRequestResponse)
async def update_quote_request(
    quote_id: str,
    data: UpdateQuoteRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.PROVIDER)),
):
    """(Admin/Provider) Répondre à une demande de devis (montant, statut)."""
    return await business_service.update_quote_request(quote_id, data)


@router.post("/quotes/{quote_id}/participants", response_model=ParticipantResponse, status_code=status.HTTP_201_CREATED)
async def add_participant(
    quote_id: str,
    data: AddParticipantRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Gérer les participants d'un événement d'entreprise."""
    return await business_service.add_participant(quote_id, data)


@router.get("/quotes/{quote_id}/participants", response_model=list)
async def list_participants(quote_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Liste des participants."""
    return await business_service.list_participants(quote_id)


@router.delete("/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_participant(participant_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Retirer un participant."""
    await business_service.remove_participant(participant_id)


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: CreateInvoiceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.PROVIDER)),
):
    """(Admin/Provider) Émettre une facture entreprise pour une demande de devis."""
    return await business_service.create_invoice(data)


@router.get("/quotes/{quote_id}/invoices", response_model=list)
async def list_invoices_for_quote(quote_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Gérer la facturation entreprise d'une demande de devis."""
    return await business_service.list_invoices_for_quote(quote_id)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice_status(
    invoice_id: str,
    data: UpdateInvoiceStatusRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.PROVIDER)),
):
    """(Admin/Provider) Mettre à jour le statut d'une facture."""
    return await business_service.update_invoice_status(invoice_id, data)
