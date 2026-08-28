from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.operator import OperatorApplicationStatus
from app.schemas.auth import TokenPayload
from app.schemas.operator import (
    CreateOperatorApplicationRequest,
    ReviewOperatorApplicationRequest,
    OperatorApplicationResponse,
)
from app.services import operator_service

router = APIRouter(prefix="/operators", tags=["Gestion des opérateurs et partenaires touristiques"])


@router.post("/applications", response_model=OperatorApplicationResponse, status_code=status.HTTP_201_CREATED)
async def submit_application(
    data: CreateOperatorApplicationRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Soumettre un dossier de reconnaissance dans une catégorie professionnelle (§36)."""
    return await operator_service.submit_application(data, applicant_id=current_user.sub)


@router.get("/applications/me", response_model=list)
async def list_my_applications(current_user: TokenPayload = Depends(get_current_user)):
    """Ses dossiers de candidature."""
    return await operator_service.list_my_applications(current_user.sub)


@router.get("/applications", response_model=list)
async def list_applications(
    status_filter: Optional[OperatorApplicationStatus] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Tous les dossiers de candidature."""
    return await operator_service.list_applications(status_filter)


@router.get("/applications/{application_id}", response_model=OperatorApplicationResponse)
async def get_application(application_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Détail d'un dossier."""
    return await operator_service.get_application(application_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN)


@router.patch("/applications/{application_id}", response_model=OperatorApplicationResponse)
async def review_application(
    application_id: str,
    data: ReviewOperatorApplicationRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Valider ou suspendre un prestataire."""
    return await operator_service.review_application(application_id, data, reviewer_id=current_user.sub)
