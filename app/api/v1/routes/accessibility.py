from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.accessibility import AccessibilityReportStatus
from app.schemas.auth import TokenPayload
from app.schemas.accessibility import (
    ReportObstacleRequest,
    ObstacleReportResponse,
    ModerateObstacleRequest,
)
from app.services import accessibility_service

router = APIRouter(prefix="/accessibility", tags=["Accessibilité et inclusion"])


@router.post("/obstacles", response_model=ObstacleReportResponse, status_code=status.HTTP_201_CREATED)
async def report_obstacle(
    data: ReportObstacleRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Signaler un obstacle d'accessibilité (§23)."""
    return await accessibility_service.report_obstacle(data, reporter_id=current_user.sub)


@router.get("/obstacles", response_model=list)
async def list_obstacle_reports(
    status_filter: Optional[AccessibilityReportStatus] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin/Modérateur) Consulter les signalements d'obstacles."""
    return await accessibility_service.list_obstacle_reports(status_filter)


@router.patch("/obstacles/{report_id}", response_model=ObstacleReportResponse)
async def moderate_obstacle_report(
    report_id: str,
    data: ModerateObstacleRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin/Modérateur) Modérer un signalement d'obstacle."""
    return await accessibility_service.moderate_obstacle_report(report_id, data, moderator_id=current_user.sub)
