from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.schemas.payment_security import (
    ConfirmTransactionRequest,
    TransactionResponse,
    FlagSuspiciousActivityRequest,
    SuspiciousFlagResponse,
)
from app.services import payment_security_service

router = APIRouter(prefix="/payment-security", tags=["Sécurité des paiements et protection"])


@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def confirm_transaction(
    data: ConfirmTransactionRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Confirmer une transaction, protégée contre le double paiement (§40)."""
    return await payment_security_service.confirm_transaction(data, payer_id=current_user.sub)


@router.get("/transactions/me", response_model=list)
async def list_my_transactions(current_user: TokenPayload = Depends(get_current_user)):
    """Historique des paiements."""
    return await payment_security_service.list_my_transactions(current_user.sub)


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Détail d'une transaction / reçu numérique."""
    return await payment_security_service.get_transaction(
        transaction_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )


@router.post("/transactions/{transaction_id}/refund", response_model=TransactionResponse)
async def mark_refunded(
    transaction_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Gérer un remboursement."""
    return await payment_security_service.mark_refunded(transaction_id)


@router.post("/flags", response_model=SuspiciousFlagResponse, status_code=status.HTTP_201_CREATED)
async def flag_suspicious_activity(
    data: FlagSuspiciousActivityRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Signaler une activité suspecte."""
    return await payment_security_service.flag_suspicious_activity(data, reporter_id=current_user.sub)


@router.get("/flags", response_model=list)
async def list_flags(current_user: TokenPayload = Depends(require_role(UserRole.ADMIN))):
    """(Admin) Activités suspectes signalées."""
    return await payment_security_service.list_flags()
