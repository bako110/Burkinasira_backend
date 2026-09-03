from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.data_quality import DataErrorReportStatus
from app.schemas.auth import TokenPayload
from app.schemas.data_quality import (
    ReportDataErrorRequest,
    DataErrorReportResponse,
    ModerateDataErrorRequest,
    DuplicateCandidateResponse,
    ResolveDuplicateRequest,
)
from app.services import data_quality_service

router = APIRouter(prefix="/data-quality", tags=["Données, cartographie et qualité"])


@router.post("/error-reports", response_model=DataErrorReportResponse, status_code=status.HTTP_201_CREATED)
async def report_error(
    data: ReportDataErrorRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Signaler une information incorrecte (§44)."""
    return await data_quality_service.report_error(data, reporter_id=current_user.sub)


@router.get("/error-reports", response_model=list)
async def list_error_reports(
    status_filter: Optional[DataErrorReportStatus] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Signalements d'informations incorrectes."""
    return await data_quality_service.list_error_reports(status_filter)


@router.get("/error-reports/received", response_model=list)
async def list_received_error_reports(
    status_filter: Optional[DataErrorReportStatus] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.GUIDE, UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Prestataire) Signalements portant sur MES fiches — hôtels, restaurants,
    transport, profil guide, événements, expériences dont je suis le propriétaire."""
    return await data_quality_service.list_reports_for_owner(current_user.sub, status_filter)


@router.get("/error-reports/received/count", response_model=int)
async def count_open_received_error_reports(
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.GUIDE, UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Prestataire) Nombre de signalements non traités sur mes fiches (pastille)."""
    return await data_quality_service.count_open_reports_for_owner(current_user.sub)


@router.patch("/error-reports/received/{report_id}", response_model=DataErrorReportResponse)
async def moderate_received_error_report(
    report_id: str,
    data: ModerateDataErrorRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.GUIDE, UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Prestataire) Traiter un signalement sur l'une de mes fiches
    (en cours d'examen / corrigé / rejeté)."""
    return await data_quality_service.moderate_error_report_as_owner(report_id, data, current_user.sub)


@router.patch("/error-reports/{report_id}", response_model=DataErrorReportResponse)
async def moderate_error_report(
    report_id: str,
    data: ModerateDataErrorRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Modérer une fiche signalée."""
    return await data_quality_service.moderate_error_report(report_id, data, reviewer_id=current_user.sub)


@router.post("/duplicates/detect", response_model=list)
async def detect_duplicates(
    item_type: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Détecter les doublons potentiels pour un type de fiche."""
    return await data_quality_service.detect_duplicates(item_type)


@router.get("/duplicates", response_model=list)
async def list_duplicates(
    item_type: Optional[str] = None,
    resolved: Optional[bool] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Doublons détectés."""
    return await data_quality_service.list_duplicates(item_type, resolved)


@router.patch("/duplicates/{duplicate_id}", response_model=DuplicateCandidateResponse)
async def resolve_duplicate(
    duplicate_id: str,
    data: ResolveDuplicateRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Marquer un doublon comme résolu."""
    return await data_quality_service.resolve_duplicate(duplicate_id, data)


@router.get("/change-history/{item_type}/{item_id}", response_model=list)
async def get_change_history(
    item_type: str,
    item_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Historique des modifications d'une fiche."""
    return await data_quality_service.get_change_history(item_type, item_id)
