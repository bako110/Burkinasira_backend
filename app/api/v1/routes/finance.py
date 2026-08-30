from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.finance import MoneyServiceType
from app.schemas.auth import TokenPayload
from app.schemas.finance import (
    CreateMoneyServiceRequest,
    UpdateMoneyServiceRequest,
    MoneyServiceDetail,
    MoneyServiceListResponse,
    CurrencyConversionRequest,
    CurrencyConversionResponse,
    WalletResponse,
    WalletTransactionResponse,
)
from app.services import finance_service

router = APIRouter(prefix="/money-services", tags=["Argent, banques et paiements"])


@router.get("", response_model=MoneyServiceListResponse)
async def list_money_services(
    type: Optional[MoneyServiceType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Banques, distributeurs, Mobile Money, bureaux de change par proximité (§13)."""
    return await finance_service.list_money_services(
        type=type, region=region, province=province, near_lat=near_lat, near_lng=near_lng,
        radius_km=radius_km, page=page, page_size=page_size,
    )


@router.post("/convert", response_model=CurrencyConversionResponse)
async def convert_currency(data: CurrencyConversionRequest):
    """Convertisseur de devises."""
    return await finance_service.convert_currency(data)


@router.get("/wallet/me", response_model=WalletResponse)
async def get_my_wallet(current_user: TokenPayload = Depends(get_current_user)):
    """Consulter son portefeuille GoTours (solde en lecture seule au Lot 1 — paiement réel en Lot 2)."""
    return await finance_service.get_or_create_wallet(current_user.sub)


@router.get("/wallet/me/transactions", response_model=list)
async def list_my_wallet_transactions(current_user: TokenPayload = Depends(get_current_user)):
    """Historique des transactions du portefeuille."""
    return await finance_service.list_wallet_transactions(current_user.sub)


@router.get("/{service_id}", response_model=MoneyServiceDetail)
async def get_money_service(service_id: str):
    """Détail d'un point banque/DAB/change."""
    return await finance_service.get_money_service(service_id)


@router.post("", response_model=MoneyServiceDetail, status_code=status.HTTP_201_CREATED)
async def create_money_service(
    data: CreateMoneyServiceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Référencer un point banque/DAB/change."""
    return await finance_service.create_money_service(data)


@router.patch("/{service_id}", response_model=MoneyServiceDetail)
async def update_money_service(
    service_id: str,
    data: UpdateMoneyServiceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Mettre à jour un point banque/DAB/change."""
    return await finance_service.update_money_service(service_id, data)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_money_service(
    service_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un point banque/DAB/change."""
    await finance_service.delete_money_service(service_id)
