from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.review import ReviewTargetType
from app.schemas.auth import TokenPayload
from app.schemas.review import (
    CreateReviewRequest,
    UpdateReviewRequest,
    ReplyReviewRequest,
    ReportReviewRequest,
    ModerateReviewRequest,
    ReviewResponse,
    ReviewListResponse,
)
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["Avis clients — GoTours Verified"])


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    data: CreateReviewRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Laisser un avis vérifié sur une réservation terminée (§37)."""
    return await review_service.create_review(data, author_id=current_user.sub)


@router.get("/me", response_model=list)
async def list_my_reviews(current_user: TokenPayload = Depends(get_current_user)):
    """Mes avis publiés."""
    return await review_service.list_my_reviews(current_user.sub)


@router.get("/moderation", response_model=list)
async def list_flagged_reviews(current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))):
    """(Admin) File de modération des avis signalés."""
    return await review_service.list_flagged_reviews()


@router.get("/target/{target_type}/{target_id}", response_model=ReviewListResponse)
async def list_reviews_for_target(
    target_type: ReviewTargetType,
    target_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Avis publiés pour une cible donnée (guide, hôtel, restaurant...), avec répartition des notes."""
    return await review_service.list_reviews_for_target(target_type.value, target_id, page, page_size)


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str):
    """Détail d'un avis."""
    return await review_service.get_review(review_id)


@router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    data: UpdateReviewRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Modifier son propre avis."""
    return await review_service.update_review(review_id, data, current_user.sub)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Supprimer son propre avis (ou n'importe lequel si admin)."""
    await review_service.delete_review(review_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN)


@router.post("/{review_id}/reply", response_model=ReviewResponse)
async def reply_to_review(
    review_id: str,
    data: ReplyReviewRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """(Professionnel concerné/Admin) Répondre publiquement à un avis."""
    return await review_service.reply_to_review(
        review_id, data, current_user.sub, is_admin=current_user.role == UserRole.ADMIN
    )


@router.post("/{review_id}/report", response_model=ReviewResponse)
async def report_review(
    review_id: str,
    data: ReportReviewRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Signaler un avis abusif, faux ou hors-sujet."""
    return await review_service.report_review(review_id, data, current_user.sub)


@router.post("/{review_id}/helpful", response_model=ReviewResponse)
async def mark_review_helpful(review_id: str):
    """Marquer un avis comme utile."""
    return await review_service.mark_helpful(review_id)


@router.patch("/{review_id}/moderate", response_model=ReviewResponse)
async def moderate_review(
    review_id: str,
    data: ModerateReviewRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Republier ou masquer définitivement un avis signalé."""
    return await review_service.moderate_review(review_id, data)
