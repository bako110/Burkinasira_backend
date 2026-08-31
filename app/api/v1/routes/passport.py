from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.schemas.passport import (
    CreateBadgeRequest,
    BadgeResponse,
    CreateChallengeRequest,
    ChallengeResponse,
    CollectStampRequest,
    PassportResponse,
)
from app.services import passport_service

router = APIRouter(prefix="/passport", tags=["Passeport FasoViva et gamification"])


@router.get("/me", response_model=PassportResponse)
async def get_my_passport(current_user: TokenPayload = Depends(get_current_user)):
    """Passeport numérique : destinations découvertes, badges, historique (§28)."""
    return await passport_service.get_my_passport(current_user.sub)


@router.post("/me/stamps", response_model=PassportResponse, status_code=status.HTTP_201_CREATED)
async def collect_stamp(
    data: CollectStampRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Collecter un tampon numérique pour une destination visitée."""
    return await passport_service.collect_stamp(data, current_user.sub)


@router.get("/badges", response_model=list)
async def list_badges():
    """Badges disponibles."""
    return await passport_service.list_badges()


@router.post("/badges", response_model=BadgeResponse, status_code=status.HTTP_201_CREATED)
async def create_badge(
    data: CreateBadgeRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Créer un badge."""
    return await passport_service.create_badge(data)


@router.get("/challenges", response_model=list)
async def list_active_challenges():
    """Défis actifs : objectifs de découverte (§28)."""
    return await passport_service.list_active_challenges()


@router.post("/challenges", response_model=ChallengeResponse, status_code=status.HTTP_201_CREATED)
async def create_challenge(
    data: CreateChallengeRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Créer un défi."""
    return await passport_service.create_challenge(data)


@router.get("/leaderboard", response_model=list)
async def get_leaderboard(limit: int = 20):
    """Classement facultatif des voyageurs."""
    return await passport_service.get_leaderboard(limit)
