from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, get_current_user_optional, require_role
from app.models.user import UserRole
from app.models.artisan import ProductCategory
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
)
from app.services import artisan_service

router = APIRouter(prefix="/market", tags=["Artisanat et marketplace — GoTours Market"])


@router.get("/artisans", response_model=list)
async def list_artisans(
    region: Optional[str] = None,
    verified_only: bool = False,
    include_all_statuses: bool = False,
    current_user: Optional[TokenPayload] = Depends(get_current_user_optional),
):
    """Artisans vérifiés (§19)."""
    is_admin = current_user is not None and current_user.role in (UserRole.ADMIN, UserRole.MODERATOR)
    return await artisan_service.list_artisans(
        region=region, verified_only=verified_only,
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
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
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


@router.get("/products/{product_id}", response_model=ProductDetail)
async def get_product(product_id: str):
    """Détail d'un produit."""
    return await artisan_service.get_product(product_id)


@router.post("/products", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: CreateProductRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Vendeur) Ajouter un produit à son catalogue. (Admin) Ajouter un produit pour un artisan donné."""
    if current_user.role == UserRole.ADMIN and data.artisan_id:
        artisan_id = data.artisan_id
    else:
        artisan = await artisan_service.get_artisan_by_user_id(current_user.sub)
        artisan_id = artisan.id
    return await artisan_service.create_product(data, artisan_id=artisan_id)


@router.patch("/products/{product_id}", response_model=ProductDetail)
async def update_product(
    product_id: str,
    data: UpdateProductRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Vendeur) Mettre à jour un produit, gérer les stocks."""
    artisan = await artisan_service.get_artisan_by_user_id(current_user.sub)
    return await artisan_service.update_product(product_id, data, artisan.id)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Vendeur) Supprimer un produit."""
    artisan = await artisan_service.get_artisan_by_user_id(current_user.sub)
    await artisan_service.delete_product(product_id, artisan.id)


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: CreateOrderRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Commander un produit (livraison ou retrait)."""
    return await artisan_service.create_order(data, buyer_id=current_user.sub)


@router.get("/orders/me", response_model=list)
async def list_my_orders(current_user: TokenPayload = Depends(get_current_user)):
    """Historique de ses commandes."""
    return await artisan_service.list_my_orders(current_user.sub)
