from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.family import FamilyServiceType
from app.schemas.auth import TokenPayload
from app.schemas.family import (
    CreateFamilyServiceRequest,
    UpdateFamilyServiceRequest,
    FamilyServiceDetail,
    FamilyServiceListResponse,
    BookChildcareRequest,
    ChildcareBookingResponse,
)
from app.services import family_service

router = APIRouter(prefix="/family-services", tags=["Famille, enfants et services du quotidien"])


@router.get("", response_model=FamilyServiceListResponse)
async def list_family_services(
    type: Optional[FamilyServiceType] = None,
    region: Optional[str] = None,
    q: Optional[str] = Query(default=None, description="Recherche texte sur le nom"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Filtrer les lieux/services adaptés aux familles (§22)."""
    return await family_service.list_family_services(type=type, region=region, q=q, page=page, page_size=page_size)


@router.get("/childcare-bookings/me", response_model=list)
async def list_my_childcare_bookings(current_user: TokenPayload = Depends(get_current_user)):
    """Suivre ses réservations de garde d'enfants."""
    return await family_service.list_my_childcare_bookings(current_user.sub)


@router.get("/{service_id}", response_model=FamilyServiceDetail)
async def get_family_service(service_id: str):
    """Détail d'un service familial."""
    return await family_service.get_family_service(service_id)


@router.post("", response_model=FamilyServiceDetail, status_code=status.HTTP_201_CREATED)
async def create_family_service(
    data: CreateFamilyServiceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.PROVIDER, UserRole.MODERATOR)),
):
    """(Provider/Admin/Moderateur) Référencer un service familial."""
    return await family_service.create_family_service(data)


@router.patch("/{service_id}", response_model=FamilyServiceDetail)
async def update_family_service(
    service_id: str,
    data: UpdateFamilyServiceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.PROVIDER, UserRole.MODERATOR)),
):
    """(Provider/Admin/Moderateur) Mettre à jour un service familial."""
    return await family_service.update_family_service(service_id, data)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_family_service(
    service_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un service familial."""
    await family_service.delete_family_service(service_id)


@router.post("/childcare-bookings", response_model=ChildcareBookingResponse, status_code=status.HTTP_201_CREATED)
async def book_childcare(
    data: BookChildcareRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Réserver un service de garde vérifié (§22)."""
    return await family_service.book_childcare(data, parent_id=current_user.sub)
