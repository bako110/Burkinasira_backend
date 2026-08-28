from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import require_role
from app.models.user import UserRole
from app.models.market import MarketPlaceType
from app.schemas.auth import TokenPayload
from app.schemas.market import (
    CreateMarketPlaceRequest,
    UpdateMarketPlaceRequest,
    MarketPlaceDetail,
    MarketPlaceListResponse,
)
from app.services import market_service

router = APIRouter(prefix="/marketplaces", tags=["Marchés et commerce local"])


@router.get("", response_model=MarketPlaceListResponse)
async def list_marketplaces(
    type: Optional[MarketPlaceType] = None,
    region: Optional[str] = None,
    product: Optional[str] = Query(default=None, description="Rechercher un produit vendu"),
    q: Optional[str] = Query(default=None, description="Recherche texte (nom, description)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Marchés, supermarchés, boutiques spécialisées, produits locaux (§20)."""
    return await market_service.list_marketplaces(
        type=type, region=region, product=product, q=q, page=page, page_size=page_size,
    )


@router.get("/{marketplace_id}", response_model=MarketPlaceDetail)
async def get_marketplace(marketplace_id: str):
    """Détail : horaires, position GPS, offres promotionnelles."""
    return await market_service.get_marketplace(marketplace_id)


@router.post("", response_model=MarketPlaceDetail, status_code=status.HTTP_201_CREATED)
async def create_marketplace(
    data: CreateMarketPlaceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.PROVIDER)),
):
    """(Provider/Admin) Référencer un marché ou un commerce local."""
    return await market_service.create_marketplace(data)


@router.patch("/{marketplace_id}", response_model=MarketPlaceDetail)
async def update_marketplace(
    marketplace_id: str,
    data: UpdateMarketPlaceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.PROVIDER)),
):
    """(Provider/Admin) Mettre à jour un marché/commerce, publier une offre."""
    return await market_service.update_marketplace(marketplace_id, data)


@router.delete("/{marketplace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_marketplace(
    marketplace_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un marché/commerce."""
    await market_service.delete_marketplace(marketplace_id)
