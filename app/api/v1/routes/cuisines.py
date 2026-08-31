from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.cuisine import EstablishmentType, DietaryTag
from app.schemas.auth import TokenPayload
from app.schemas.cuisine import (
    CreateRestaurantRequest,
    UpdateRestaurantRequest,
    RestaurantDetail,
    RestaurantListResponse,
)
from app.services import cuisine_service

router = APIRouter(prefix="/restaurants", tags=["Restauration — FasoViva Food"])


@router.get("", response_model=RestaurantListResponse)
async def list_restaurants(
    type: Optional[EstablishmentType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    city: Optional[str] = None,
    dietary_tag: Optional[DietaryTag] = None,
    q: Optional[str] = Query(default=None, description="Recherche texte (nom, description, style)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Filtrer les restaurants (famille, végétarien, budget, proximité) (§8)."""
    return await cuisine_service.list_restaurants(
        type=type, region=region, province=province, city=city, dietary_tag=dietary_tag,
        q=q, page=page, page_size=page_size,
    )


@router.get("/me/list", response_model=list)
async def list_my_restaurants(
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Provider) Liste de mes restaurants, tous statuts confondus."""
    return await cuisine_service.list_my_restaurants(current_user.sub)


@router.get("/{restaurant_id}", response_model=RestaurantDetail)
async def get_restaurant(restaurant_id: str):
    """Fiche détaillée d'un restaurant, avec menu si disponible."""
    return await cuisine_service.get_restaurant(restaurant_id)


@router.post("", response_model=RestaurantDetail, status_code=status.HTTP_201_CREATED)
async def create_restaurant(
    data: CreateRestaurantRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Provider) Ajouter un restaurant. Publié directement si le compte est déjà
    vérifié, sinon enregistré en brouillon en attendant l'approbation admin."""
    return await cuisine_service.create_restaurant(
        data, owner_id=current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )


@router.patch("/{restaurant_id}", response_model=RestaurantDetail)
async def update_restaurant(
    restaurant_id: str,
    data: UpdateRestaurantRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Owner/Admin) Mettre à jour un restaurant."""
    return await cuisine_service.update_restaurant(
        restaurant_id, data, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )


@router.delete("/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_restaurant(
    restaurant_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Owner/Admin) Supprimer un restaurant."""
    await cuisine_service.delete_restaurant(
        restaurant_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )
