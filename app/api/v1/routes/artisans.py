from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, get_current_user_optional, require_role, require_verified_provider
from app.models.user import UserRole
from app.models.artisan import ProductCategory, ArtisanOrderStatus, DeliverySettlementStatus
from app.schemas.auth import TokenPayload
from app.schemas.artisan import (
    CreateArtisanRequest,
    UpdateArtisanRequest,
    ArtisanResponse,
    CreateProductRequest,
    UpdateProductRequest,
    ProductDetail,
    ProductListResponse,
    CreateOrderRequest,
    OrderResponse,
    UpdateOrderStatusRequest,
    CreateDeliveryAgencyRequest,
    UpdateDeliveryAgencyRequest,
    DeliveryAgencyResponse,
    UpsertDeliveryFeeRuleRequest,
    DeliveryFeeRuleResponse,
    DeliveryFeeQuoteRequest,
    DeliveryFeeQuote,
    DeliveryDueResponse,
    CreateSettlementRequest,
    SettlementResponse,
)
from app.services import (
    artisan_service,
    delivery_fee_service,
    delivery_agency_service,
    delivery_settlement_service,
)

router = APIRouter(prefix="/market", tags=["Artisanat et marketplace — BurkinaSira Market"])


@router.get("/artisans", response_model=list)
async def list_artisans(
    region: Optional[str] = None,
    province: Optional[str] = None,
    verified_only: bool = False,
    include_all_statuses: bool = False,
    current_user: Optional[TokenPayload] = Depends(get_current_user_optional),
):
    """Artisans vérifiés (§19)."""
    is_admin = current_user is not None and current_user.role in (UserRole.ADMIN, UserRole.MODERATOR)
    return await artisan_service.list_artisans(
        region=region, province=province, verified_only=verified_only,
        include_all_statuses=include_all_statuses and is_admin,
    )


@router.get("/artisans/me", response_model=ArtisanResponse)
async def get_my_artisan_profile(
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Vendeur) Consulter son propre profil artisan."""
    return await artisan_service.get_artisan_by_user_id(current_user.sub)


@router.get("/artisans/{artisan_id}", response_model=ArtisanResponse)
async def get_artisan(artisan_id: str):
    """Profil public d'un artisan, avec histoire du fabricant."""
    return await artisan_service.get_artisan(artisan_id)


@router.post("/artisans", response_model=ArtisanResponse, status_code=status.HTTP_201_CREATED)
async def create_artisan(
    data: CreateArtisanRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Vendeur) Créer son profil artisan."""
    return await artisan_service.create_artisan(data, user_id=current_user.sub)


@router.patch("/artisans/me", response_model=ArtisanResponse)
async def update_my_artisan_profile(
    data: UpdateArtisanRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Vendeur) Mettre à jour son profil artisan."""
    return await artisan_service.update_artisan(current_user.sub, data)


@router.delete("/artisans/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_artisan_profile(
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Vendeur) Supprimer son propre profil artisan."""
    await artisan_service.delete_artisan(current_user.sub)


@router.patch("/artisans/{artisan_id}", response_model=ArtisanResponse)
async def update_artisan_by_id(
    artisan_id: str,
    data: UpdateArtisanRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour le profil d'un artisan par son identifiant."""
    return await artisan_service.update_artisan_by_id(artisan_id, data)


@router.delete("/artisans/{artisan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artisan(
    artisan_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer le profil d'un artisan."""
    await artisan_service.delete_artisan(current_user.sub, is_admin=True, target_artisan_id=artisan_id)


# Left ADMIN-only: verification/trust status change on a provider account, not content management.
@router.post("/artisans/{artisan_id}/verify", response_model=ArtisanResponse)
async def verify_artisan(
    artisan_id: str,
    is_verified: bool = True,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Vérifier un artisan (§37)."""
    return await artisan_service.set_verification_status(artisan_id, is_verified)


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    category: Optional[ProductCategory] = None,
    artisan_id: Optional[str] = None,
    q: Optional[str] = Query(default=None, description="Recherche texte (nom, description)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Rechercher / filtrer un produit (§19)."""
    return await artisan_service.list_products(category=category, artisan_id=artisan_id, q=q, page=page, page_size=page_size)


@router.get("/products/me/list", response_model=list)
async def list_my_products(
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Vendeur) Liste de mes produits, tous statuts confondus."""
    artisan = await artisan_service.get_artisan_by_user_id(current_user.sub)
    return await artisan_service.list_my_products(artisan.id)


@router.get("/products/{product_id}", response_model=ProductDetail)
async def get_product(product_id: str):
    """Détail d'un produit."""
    return await artisan_service.get_product(product_id)


@router.post("/products", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: CreateProductRequest,
    current_user: TokenPayload = Depends(require_verified_provider),
):
    """(Vendeur) Ajouter un produit à son catalogue. (Admin) Ajouter un produit pour un artisan donné, ou pour la vitrine BurkinaSira si aucun n'est précisé."""
    if current_user.role == UserRole.ADMIN:
        if data.artisan_id:
            artisan_id = data.artisan_id
        else:
            artisan = await artisan_service.get_or_create_official_artisan(current_user.sub)
            artisan_id = artisan.id
    else:
        artisan = await artisan_service.get_artisan_by_user_id(current_user.sub)
        artisan_id = artisan.id
    return await artisan_service.create_product(data, artisan_id=artisan_id)


@router.patch("/products/{product_id}", response_model=ProductDetail)
async def update_product(
    product_id: str,
    data: UpdateProductRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Vendeur) Mettre à jour un produit, gérer les stocks. (Admin/Moderateur) Mettre à jour n'importe quel produit."""
    if current_user.role in (UserRole.ADMIN, UserRole.MODERATOR):
        return await artisan_service.update_product(product_id, data, current_artisan_id=None, is_admin=True)
    artisan = await artisan_service.get_artisan_by_user_id(current_user.sub)
    return await artisan_service.update_product(product_id, data, current_artisan_id=artisan.id)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Vendeur) Supprimer un produit. (Admin) Supprimer n'importe quel produit."""
    if current_user.role == UserRole.ADMIN:
        await artisan_service.delete_product(product_id, current_artisan_id=None, is_admin=True)
        return
    artisan = await artisan_service.get_artisan_by_user_id(current_user.sub)
    await artisan_service.delete_product(product_id, current_artisan_id=artisan.id)


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: CreateOrderRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Commander un produit (livraison ou retrait).

    En mode livraison, `delivery_region` est obligatoire : les frais de livraison
    sont calculés automatiquement d'après la grille par région (agence de
    livraison) et ajoutés au total.
    """
    return await artisan_service.create_order(data, buyer_id=current_user.sub)


@router.get("/orders/me", response_model=list)
async def list_my_orders(current_user: TokenPayload = Depends(get_current_user)):
    """Historique de ses commandes (en tant qu'acheteur)."""
    return await artisan_service.list_my_orders(current_user.sub)


@router.get("/orders/received", response_model=list)
async def list_received_orders(
    status: Optional[ArtisanOrderStatus] = Query(default=None),
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Vendeur) Commandes reçues sur ses produits, avec leur suivi de livraison."""
    return await artisan_service.list_received_orders(
        current_user.sub, status_filter=status.value if status else None,
    )


@router.get("/orders", response_model=list)
async def list_orders(
    status: Optional[ArtisanOrderStatus] = Query(default=None),
    agency_id: Optional[str] = None,
    artisan_id: Optional[str] = None,
    settlement_status: Optional[DeliverySettlementStatus] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin/Modérateur) Toutes les commandes artisanales, filtrables."""
    return await artisan_service.list_orders(
        status_filter=status.value if status else None,
        agency_id=agency_id,
        artisan_id=artisan_id,
        settlement_status=settlement_status.value if settlement_status else None,
        page=page,
        page_size=page_size,
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Détail d'une commande : acheteur, artisan propriétaire du produit, ou staff."""
    is_staff = current_user.role in (UserRole.ADMIN, UserRole.MODERATOR)
    return await artisan_service.get_order(order_id, requester_id=current_user.sub, is_staff=is_staff)


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    data: UpdateOrderStatusRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin/Modérateur) Faire avancer le statut de livraison d'une commande.

    Transitions : pending → confirmed → handed_to_agency → in_delivery →
    delivered ; cancelled/returned réapprovisionnent le stock et retirent le
    montant du dû à l'agence.
    """
    return await artisan_service.update_order_status(order_id, data, actor_id=current_user.sub)


# ============================================
# AGENCES DE LIVRAISON (§19)
# ============================================

@router.get("/delivery-agencies", response_model=list)
async def list_delivery_agencies(
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin/Modérateur) Liste des agences de livraison."""
    return await delivery_agency_service.list_agencies()


@router.post("/delivery-agencies", response_model=DeliveryAgencyResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_agency(
    data: CreateDeliveryAgencyRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Créer une agence de livraison."""
    return await delivery_agency_service.create_agency(data)


@router.patch("/delivery-agencies/{agency_id}", response_model=DeliveryAgencyResponse)
async def update_delivery_agency(
    agency_id: str,
    data: UpdateDeliveryAgencyRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Mettre à jour une agence de livraison."""
    return await delivery_agency_service.update_agency(agency_id, data)


@router.delete("/delivery-agencies/{agency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery_agency(
    agency_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer une agence (refusé si une règle de frais l'utilise)."""
    await delivery_agency_service.delete_agency(agency_id)


# ============================================
# RÈGLEMENTS AUX AGENCES DE LIVRAISON (§19)
# ============================================

@router.get("/delivery-settlements/due", response_model=DeliveryDueResponse)
async def list_delivery_due(
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Montants dus aux agences : commandes livrées, frais > 0, non réglées."""
    return await delivery_settlement_service.list_due_by_agency()


@router.post("/delivery-settlements", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_settlement(
    data: CreateSettlementRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Marquer un lot de commandes livrées comme réglé à l'agence."""
    return await delivery_settlement_service.settle(data, actor_id=current_user.sub)


@router.get("/delivery-settlements", response_model=list)
async def list_delivery_settlements(
    agency_id: Optional[str] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Historique des règlements versés aux agences."""
    return await delivery_settlement_service.list_settlements(agency_id=agency_id)


# ============================================
# FRAIS DE LIVRAISON — GRILLE PAR RÉGION (§19)
# ============================================

@router.post("/delivery-fees/quote", response_model=DeliveryFeeQuote)
async def quote_delivery_fee(data: DeliveryFeeQuoteRequest):
    """Estimer les frais de livraison pour une région et un sous-total (avant commande)."""
    return await delivery_fee_service.compute_delivery_fee(data.region, data.subtotal)


@router.get("/delivery-fees", response_model=list)
async def list_delivery_fee_rules(
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin/Modérateur) Grille complète des frais de livraison."""
    return await delivery_fee_service.list_rules()


@router.put("/delivery-fees", response_model=DeliveryFeeRuleResponse)
async def upsert_delivery_fee_rule(
    data: UpsertDeliveryFeeRuleRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Créer ou mettre à jour le tarif d'une région (`region="*"` = tarif par défaut)."""
    return await delivery_fee_service.upsert_rule(data)


@router.delete("/delivery-fees/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery_fee_rule(
    rule_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer le tarif d'une région."""
    await delivery_fee_service.delete_rule(rule_id)
