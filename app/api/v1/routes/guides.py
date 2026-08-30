from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, get_current_user_optional, require_role
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.models.booking import BookingStatus
from app.schemas.guide import (
    CreateGuideProfileRequest,
    UpdateGuideProfileRequest,
    RejectGuideRequest,
    GuideDetail,
    GuideListResponse,
)
from app.schemas.review import ReviewListResponse
from app.schemas.guide_analytics import GuideAnalyticsSummary
from app.services import guide_service, booking_service, review_service, guide_analytics_service

router = APIRouter(prefix="/guides", tags=["Guides touristiques"])


@router.get("", response_model=GuideListResponse)
async def list_guides(
    region: Optional[str] = None,
    province: Optional[str] = None,
    language: Optional[str] = None,
    specialty: Optional[str] = None,
    verified_only: bool = False,
    include_all_statuses: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: Optional[TokenPayload] = Depends(get_current_user_optional),
):
    """Rechercher des guides touristiques (§6)."""
    is_admin = current_user is not None and current_user.role in (UserRole.ADMIN, UserRole.MODERATOR)
    return await guide_service.list_guides(
        region=region, province=province, language=language, specialty=specialty,
        verified_only=verified_only, page=page, page_size=page_size,
        include_all_statuses=include_all_statuses and is_admin,
    )


@router.get("/me", response_model=GuideDetail)
async def get_my_guide_profile(
    current_user: TokenPayload = Depends(require_role(UserRole.GUIDE, UserRole.ADMIN)),
):
    """(Guide) Consulter son propre profil."""
    return await guide_service.get_guide_by_user_id(current_user.sub)


@router.get("/me/bookings", response_model=list)
async def list_my_guide_bookings(
    status_filter: Optional[BookingStatus] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.GUIDE, UserRole.ADMIN)),
):
    """(Guide) Réservations reçues sur son propre profil."""
    guide = await guide_service.get_guide_by_user_id(current_user.sub)
    return await booking_service.list_guide_bookings(guide.id, status_filter)


@router.get("/me/reviews", response_model=ReviewListResponse)
async def list_my_guide_reviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: TokenPayload = Depends(require_role(UserRole.GUIDE, UserRole.ADMIN)),
):
    """(Guide) Avis reçus sur son propre profil, avec répartition des notes."""
    guide = await guide_service.get_guide_by_user_id(current_user.sub)
    return await review_service.list_reviews_for_target("guide", guide.id, page, page_size)


@router.get("/me/analytics", response_model=GuideAnalyticsSummary)
async def get_my_guide_analytics(
    current_user: TokenPayload = Depends(require_role(UserRole.GUIDE, UserRole.ADMIN)),
):
    """(Guide) Statistiques de clients et de revenus (quotidien/mensuel/annuel)."""
    guide = await guide_service.get_guide_by_user_id(current_user.sub)
    return await guide_analytics_service.get_guide_analytics(guide.id, guide.currency)


@router.get("/{guide_id}", response_model=GuideDetail)
async def get_guide(guide_id: str):
    """Profil public d'un guide."""
    return await guide_service.get_guide(guide_id)


@router.post("", response_model=GuideDetail, status_code=status.HTTP_201_CREATED)
async def create_guide_profile(
    data: CreateGuideProfileRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.GUIDE, UserRole.ADMIN)),
):
    """(Guide) Créer son profil professionnel."""
    return await guide_service.create_guide_profile(data, user_id=current_user.sub)


@router.patch("/me", response_model=GuideDetail)
async def update_my_guide_profile(
    data: UpdateGuideProfileRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.GUIDE, UserRole.ADMIN)),
):
    """(Guide) Mettre à jour son profil et ses disponibilités générales."""
    return await guide_service.update_guide_profile(current_user.sub, data)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_guide_profile(
    current_user: TokenPayload = Depends(require_role(UserRole.GUIDE, UserRole.ADMIN)),
):
    """(Guide) Supprimer son propre profil."""
    await guide_service.delete_guide_profile(current_user.sub)


@router.patch("/{guide_id}", response_model=GuideDetail)
async def update_guide_profile_by_id(
    guide_id: str,
    data: UpdateGuideProfileRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Mettre à jour le profil d'un guide par son identifiant."""
    return await guide_service.update_guide_profile_by_id(guide_id, data)


@router.delete("/{guide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guide_profile(
    guide_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer le profil d'un guide."""
    await guide_service.delete_guide_profile(current_user.sub, is_admin=True, target_guide_id=guide_id)


@router.post("/{guide_id}/verify", response_model=GuideDetail)
async def verify_guide(
    guide_id: str,
    is_verified: bool = True,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Vérifier un guide (§37 GoTours Verified)."""
    return await guide_service.set_verification_status(guide_id, is_verified)


@router.post("/{guide_id}/approve", response_model=GuideDetail)
async def approve_guide(
    guide_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Approuver un guide : active son profil et son compte."""
    return await guide_service.approve_guide(guide_id)


@router.post("/{guide_id}/reject", response_model=GuideDetail)
async def reject_guide(
    guide_id: str,
    data: RejectGuideRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Rejeter un guide avec un motif ; il peut corriger et resoumettre."""
    return await guide_service.reject_guide(guide_id, data.reason)
