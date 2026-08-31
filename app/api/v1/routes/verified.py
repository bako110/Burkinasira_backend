from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.verified import DisputeStatus
from app.schemas.auth import TokenPayload
from app.schemas.verified import (
    SubmitVerificationRequest,
    ReviewVerificationRequest,
    ReviewAccountRequest,
    VerificationRequestResponse,
    PendingAccountSummary,
    CreateDisputeRequest,
    ResolveDisputeRequest,
    DisputeResponse,
    ReportSuspiciousRequest,
    SuspiciousReportResponse,
)
from app.services import verified_service

router = APIRouter(prefix="/verified", tags=["FasoViva Verified — confiance"])


@router.post("/verification-requests", response_model=VerificationRequestResponse, status_code=status.HTTP_201_CREATED)
async def submit_verification(
    data: SubmitVerificationRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Vérifier son identité / ses documents professionnels (§37)."""
    return await verified_service.submit_verification(data, user_id=current_user.sub)


@router.get("/verification-requests/me", response_model=list)
async def list_my_verifications(current_user: TokenPayload = Depends(get_current_user)):
    """Ses demandes de vérification."""
    return await verified_service.list_my_verifications(current_user.sub)


@router.get("/verification-requests", response_model=list)
async def list_pending_verifications(current_user: TokenPayload = Depends(require_role(UserRole.ADMIN))):
    """(Admin) Demandes de vérification en attente."""
    return await verified_service.list_pending_verifications()


@router.patch("/verification-requests/{request_id}", response_model=VerificationRequestResponse)
async def review_verification(
    request_id: str,
    data: ReviewVerificationRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Approuver/rejeter une demande de vérification précise."""
    return await verified_service.review_verification(request_id, data, reviewer_id=current_user.sub)


@router.patch("/accounts/{user_id}/review", response_model=PendingAccountSummary)
async def review_account(
    user_id: str,
    data: ReviewAccountRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Approuver/rejeter le compte pro d'un utilisateur, qu'il ait ou
    non déjà soumis un document de vérification. Publie automatiquement ses
    établissements en brouillon si approuvé."""
    return await verified_service.review_account(user_id, data, reviewer_id=current_user.sub)


@router.post("/reports", response_model=SuspiciousReportResponse, status_code=status.HTTP_201_CREATED)
async def report_suspicious(
    data: ReportSuspiciousRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Signaler un profil suspect ou un contenu suspect."""
    return await verified_service.report_suspicious(data, reporter_id=current_user.sub)


@router.post("/disputes", response_model=DisputeResponse, status_code=status.HTTP_201_CREATED)
async def open_dispute(
    data: CreateDisputeRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Ouvrir un dossier au centre de résolution des litiges."""
    return await verified_service.open_dispute(data, complainant_id=current_user.sub)


@router.get("/disputes/me", response_model=list)
async def list_my_disputes(current_user: TokenPayload = Depends(get_current_user)):
    """Ses litiges ouverts."""
    return await verified_service.list_my_disputes(current_user.sub)


@router.get("/disputes", response_model=list)
async def list_all_disputes(
    status_filter: Optional[DisputeStatus] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Tous les litiges."""
    return await verified_service.list_all_disputes(status_filter)


@router.patch("/disputes/{dispute_id}", response_model=DisputeResponse)
async def resolve_dispute(
    dispute_id: str,
    data: ResolveDisputeRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Résoudre un litige."""
    return await verified_service.resolve_dispute(dispute_id, data, resolver_id=current_user.sub)
